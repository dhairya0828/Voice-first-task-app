from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Task, TaskEvent, TaskEventType, TaskStatus


def _utc_now() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0)


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", value.lower()).strip()


def _create_event(
    db: Session,
    task: Task,
    user_id: int,
    event_type: TaskEventType,
    payload: Optional[dict] = None,
) -> None:
    event = TaskEvent(task_id=task.id, user_id=user_id, event_type=event_type, payload=payload or {})
    db.add(event)


def create_task(
    db: Session,
    user_id: int,
    title: str,
    description: Optional[str],
    due_date: Optional[datetime],
    source: str,
) -> Task:
    normalized_due_date = _normalize_datetime(due_date)
    task = Task(
        user_id=user_id,
        title=title.strip(),
        description=description.strip() if description else None,
        due_date=normalized_due_date,
        original_due_date=normalized_due_date,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.flush()
    _create_event(
        db,
        task,
        user_id,
        TaskEventType.CREATED,
        payload={
            "source": source,
            "title": task.title,
            "due_date": normalized_due_date.isoformat() if normalized_due_date else None,
        },
    )
    db.commit()
    db.refresh(task)
    return task


def get_task_for_user(db: Session, user_id: int, task_id: int) -> Task:
    task = db.query(Task).filter(Task.user_id == user_id, Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def list_tasks(db: Session, user_id: int, status_filter: Optional[TaskStatus] = None) -> list[Task]:
    query = db.query(Task).filter(Task.user_id == user_id)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    return query.order_by(Task.created_at.desc()).all()


def complete_task(db: Session, task: Task, user_id: int, source: str) -> Task:
    if task.status == TaskStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled task cannot be completed")

    task.status = TaskStatus.COMPLETED
    task.completed_at = _utc_now()
    task.updated_at = _utc_now()
    _create_event(db, task, user_id, TaskEventType.COMPLETED, payload={"source": source})
    db.commit()
    db.refresh(task)
    return task


def cancel_task(db: Session, task: Task, user_id: int, source: str) -> Task:
    task.status = TaskStatus.CANCELLED
    task.cancelled_at = _utc_now()
    task.updated_at = _utc_now()
    _create_event(db, task, user_id, TaskEventType.CANCELLED, payload={"source": source})
    db.commit()
    db.refresh(task)
    return task


def delay_task(
    db: Session,
    task: Task,
    user_id: int,
    source: str,
    days: Optional[int] = None,
    new_due_date: Optional[datetime] = None,
) -> Task:
    if task.status != TaskStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending tasks can be delayed")

    if new_due_date:
        previous_due = task.due_date
        task.due_date = _normalize_datetime(new_due_date)
    elif days:
        anchor = task.due_date or _utc_now()
        previous_due = task.due_date
        task.due_date = anchor + timedelta(days=days)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either days or new_due_date is required")

    task.delayed_count += 1
    task.updated_at = _utc_now()

    _create_event(
        db,
        task,
        user_id,
        TaskEventType.DELAYED,
        payload={
            "source": source,
            "previous_due_date": previous_due.isoformat() if previous_due else None,
            "new_due_date": task.due_date.isoformat() if task.due_date else None,
            "days": days,
        },
    )
    db.commit()
    db.refresh(task)
    return task


def update_task(
    db: Session,
    task: Task,
    user_id: int,
    title: Optional[str],
    description: Optional[str],
    due_date: Optional[datetime],
) -> Task:
    changed_fields: dict[str, Optional[str]] = {}

    if title is not None:
        task.title = title.strip()
        changed_fields["title"] = task.title
    if description is not None:
        task.description = description.strip() if description else None
        changed_fields["description"] = task.description
    if due_date is not None:
        normalized_due_date = _normalize_datetime(due_date)
        task.due_date = normalized_due_date
        if task.original_due_date is None:
            task.original_due_date = normalized_due_date
        changed_fields["due_date"] = normalized_due_date.isoformat() if normalized_due_date else None

    task.updated_at = _utc_now()
    _create_event(db, task, user_id, TaskEventType.UPDATED, payload=changed_fields)
    db.commit()
    db.refresh(task)
    return task


def find_best_matching_task(
    db: Session,
    user_id: int,
    task_query: str,
    pending_only: bool = True,
    threshold: float = 0.42,
) -> Optional[Task]:
    if not task_query.strip():
        return None

    query = db.query(Task).filter(Task.user_id == user_id)
    if pending_only:
        query = query.filter(Task.status == TaskStatus.PENDING)

    candidates = query.order_by(Task.updated_at.desc()).all()
    if not candidates:
        return None

    normalized_query = _normalize_text(task_query)
    best_task: Optional[Task] = None
    best_score = 0.0

    for candidate in candidates:
        normalized_title = _normalize_text(candidate.title)
        if not normalized_title:
            continue

        score = SequenceMatcher(None, normalized_query, normalized_title).ratio()
        if normalized_query in normalized_title:
            score += 0.25

        if score > best_score:
            best_score = score
            best_task = candidate

    if best_score < threshold:
        return None
    return best_task
