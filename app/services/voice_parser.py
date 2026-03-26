from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from dateparser.search import search_dates

from app.schemas import VoiceInterpretation

ACTION_PATTERNS = {
    "complete": re.compile(r"\b(complete|completed|done|finish|finished|published|submitted|shipped|delivered)\b", re.IGNORECASE),
    "cancel": re.compile(r"\b(cancel|cancelled|canceled|drop|delete)\b", re.IGNORECASE),
    "delay": re.compile(r"\b(delay|postpone|push|reschedule|snooze)\b", re.IGNORECASE),
}

LEADING_CREATE_PHRASES = [
    r"^remind me to\s+",
    r"^add (?:a )?task to\s+",
    r"^add\s+",
    r"^create (?:a )?task to\s+",
    r"^create task\s+",
    r"^i need to\s+",
    r"^note to\s+",
]

DELAY_AMOUNT_PATTERN = re.compile(r"\b(\d+)\s*(day|days|d|week|weeks|w|hour|hours|h)\b", re.IGNORECASE)
TIME_TOKEN_PATTERN = re.compile(
    r"\b(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}:\d{2}|noon|midnight|morning|afternoon|evening|night|tonight)\b",
    re.IGNORECASE,
)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _detect_action(text: str) -> str:
    for action in ("complete", "cancel", "delay"):
        if ACTION_PATTERNS[action].search(text):
            return action
    return "create"


def _parse_datetime(text: str, relative_base: datetime) -> Tuple[Optional[datetime], Optional[str]]:
    matches = search_dates(
        text,
        languages=["en"],
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": relative_base,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": "UTC",
            "TO_TIMEZONE": "UTC",
        },
    )

    if not matches:
        return None, None

    for snippet, dt in matches:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        if snippet and not TIME_TOKEN_PATTERN.search(snippet):
            dt = dt.replace(hour=23, minute=59, second=0, microsecond=0)

        if dt >= relative_base:
            return dt.replace(microsecond=0), snippet

    snippet, dt = matches[0]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    if snippet and not TIME_TOKEN_PATTERN.search(snippet):
        dt = dt.replace(hour=23, minute=59, second=0, microsecond=0)
    return dt.replace(microsecond=0), snippet


def _extract_create_title(normalized: str, date_snippet: Optional[str]) -> str:
    title = normalized

    for pattern in LEADING_CREATE_PHRASES:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)

    if date_snippet:
        title = re.sub(re.escape(date_snippet), "", title, count=1, flags=re.IGNORECASE)

    title = re.sub(r"\b(by|on|at|before|around|due)\b\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" .,!?")

    if not title:
        title = normalized.strip(" .,!?")

    if len(title) > 180:
        title = title[:180].rstrip()

    if title and title[0].islower():
        title = title[0].upper() + title[1:]

    return title


def _extract_query_for_action(action: str, normalized: str) -> str:
    query = normalized
    query = query.replace("i've", "i have").replace("we've", "we have")

    if action == "complete":
        query = re.sub(
            r"\b(please|mark|set|task|as|complete|completed|done|finish|finished|published|submitted|shipped|delivered|i|we|have|just|already)\b",
            " ",
            query,
            flags=re.IGNORECASE,
        )
    elif action == "cancel":
        query = re.sub(r"\b(please|cancel|cancelled|canceled|drop|delete|task)\b", " ", query, flags=re.IGNORECASE)
    elif action == "delay":
        query = re.sub(r"\b(please|delay|postpone|push|reschedule|snooze|task)\b", " ", query, flags=re.IGNORECASE)
        query = DELAY_AMOUNT_PATTERN.sub(" ", query)
        query = re.sub(r"\b(by|for|to|until|till)\b.*$", " ", query, flags=re.IGNORECASE)

    query = re.sub(r"\s+", " ", query).strip(" .,!?")
    return query


def _parse_delay_details(normalized: str, relative_base: datetime) -> Tuple[Optional[int], Optional[datetime]]:
    delay_days: Optional[int] = None
    target_due_date: Optional[datetime] = None

    match = DELAY_AMOUNT_PATTERN.search(normalized)
    if match:
        value = int(match.group(1))
        unit = match.group(2).lower()

        if unit.startswith("week") or unit == "w":
            delay_days = value * 7
        elif unit.startswith("hour") or unit == "h":
            delay_days = 1 if value > 0 else None
        else:
            delay_days = value

    to_clause = re.search(r"\b(?:to|until|till)\s+(.+)$", normalized, flags=re.IGNORECASE)
    if to_clause:
        parsed_dt, _ = _parse_datetime(to_clause.group(1), relative_base)
        if parsed_dt:
            target_due_date = parsed_dt

    if delay_days is None and target_due_date is None:
        if re.search(r"\btomorrow\b", normalized, flags=re.IGNORECASE):
            delay_days = 1

    return delay_days, target_due_date


def interpret_voice_command(text: str, now: Optional[datetime] = None) -> VoiceInterpretation:
    reference_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    original_text = text.strip()
    normalized = _normalize_text(original_text)

    action = _detect_action(normalized)
    warnings: list[str] = []
    follow_up: Optional[str] = None
    confidence = 0.55

    extracted_title: Optional[str] = None
    extracted_description: Optional[str] = None
    extracted_due_date: Optional[datetime] = None
    task_query: Optional[str] = None
    delay_days: Optional[int] = None
    target_due_date: Optional[datetime] = None

    if action == "create":
        extracted_due_date, date_snippet = _parse_datetime(normalized, reference_now)
        extracted_title = _extract_create_title(normalized, date_snippet)
        extracted_description = original_text

        confidence = 0.65
        if extracted_due_date is not None:
            confidence += 0.2
        else:
            warnings.append("No due date found. Task will remain pending without a deadline.")
            follow_up = "What due date should I set for this task?"

        if len(extracted_title.split()) >= 2:
            confidence += 0.1
        else:
            warnings.append("Task title looks too short. Consider editing before saving.")

    elif action in {"complete", "cancel"}:
        task_query = _extract_query_for_action(action, normalized)
        confidence = 0.72

        if task_query:
            confidence += 0.18
        else:
            warnings.append(f"I could not identify which task to {action}.")
            follow_up = f"Which task should I {action}?"

    else:
        task_query = _extract_query_for_action("delay", normalized)
        delay_days, target_due_date = _parse_delay_details(normalized, reference_now)
        confidence = 0.68

        if task_query:
            confidence += 0.12
        else:
            warnings.append("I could not identify which task to delay.")

        if delay_days is None and target_due_date is None:
            warnings.append("No delay amount or target due date found.")
            follow_up = "How much should I delay it?"
        else:
            confidence += 0.12

    confidence = max(0.0, min(1.0, round(confidence, 2)))

    return VoiceInterpretation(
        original_text=original_text,
        normalized_text=normalized,
        action=action,
        confidence=confidence,
        warnings=warnings,
        extracted_title=extracted_title,
        extracted_description=extracted_description,
        extracted_due_date=extracted_due_date,
        task_query=task_query,
        delay_days=delay_days,
        target_due_date=target_due_date,
        follow_up_question=follow_up,
    )
