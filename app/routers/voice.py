from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import VoiceExecuteRequest, VoiceExecuteResponse, VoiceInterpretRequest, VoiceInterpretation
from app.services.task_service import (
    cancel_task,
    complete_task,
    create_task,
    delay_task,
    find_recent_duplicate_task,
    find_best_matching_task,
)
from app.services.voice_parser import interpret_voice_command

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/interpret", response_model=VoiceInterpretation)
def interpret_command(payload: VoiceInterpretRequest) -> VoiceInterpretation:
    return interpret_voice_command(payload.text)


def _confirmation_reason(interpretation: VoiceInterpretation, confidence_threshold: float) -> Optional[str]:
    if interpretation.follow_up_question:
        return interpretation.follow_up_question

    if interpretation.confidence < confidence_threshold:
        return "I am not highly confident about this command. Please confirm to execute."

    if interpretation.warnings:
        return interpretation.warnings[0]

    return None


@router.post("/execute", response_model=VoiceExecuteResponse)
def execute_command(
    payload: VoiceExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VoiceExecuteResponse:
    interpretation = interpret_voice_command(payload.text)

    if interpretation.action == "create":
        if not interpretation.extracted_title:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not derive task title")

        duplicate_task = find_recent_duplicate_task(
            db,
            current_user.id,
            title=interpretation.extracted_title,
            due_date=interpretation.extracted_due_date,
        )
        if duplicate_task and not payload.force:
            return VoiceExecuteResponse(
                message="Possible duplicate task detected. Confirm to create another one.",
                interpretation=interpretation,
                task=duplicate_task,
                requires_confirmation=True,
                confirmation_reason="A similar pending task was created recently.",
            )

        confirmation_reason = _confirmation_reason(interpretation, confidence_threshold=0.8)
        if confirmation_reason and not payload.force:
            return VoiceExecuteResponse(
                message="This command needs confirmation before execution.",
                interpretation=interpretation,
                requires_confirmation=True,
                confirmation_reason=confirmation_reason,
            )

        task = create_task(
            db,
            current_user.id,
            title=interpretation.extracted_title,
            description=interpretation.extracted_description,
            due_date=interpretation.extracted_due_date,
            source="voice",
        )
        return VoiceExecuteResponse(message="Task created from voice command", interpretation=interpretation, task=task)

    if not interpretation.task_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not identify target task from voice command",
        )

    confirmation_reason = _confirmation_reason(interpretation, confidence_threshold=0.74)
    if confirmation_reason and not payload.force:
        return VoiceExecuteResponse(
            message="This command needs confirmation before execution.",
            interpretation=interpretation,
            requires_confirmation=True,
            confirmation_reason=confirmation_reason,
        )

    task = find_best_matching_task(db, current_user.id, interpretation.task_query, pending_only=True, threshold=0.58)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching pending task found. Try a more specific task title.",
        )

    if interpretation.action == "complete":
        updated = complete_task(db, task, current_user.id, source="voice")
        return VoiceExecuteResponse(message=f"Task '{updated.title}' marked as complete", interpretation=interpretation, task=updated)

    if interpretation.action == "cancel":
        updated = cancel_task(db, task, current_user.id, source="voice")
        return VoiceExecuteResponse(message=f"Task '{updated.title}' was cancelled", interpretation=interpretation, task=updated)

    if interpretation.target_due_date is None and interpretation.delay_days is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not determine how much to delay the task",
        )

    updated = delay_task(
        db,
        task,
        current_user.id,
        source="voice",
        days=interpretation.delay_days,
        new_due_date=interpretation.target_due_date,
    )
    return VoiceExecuteResponse(message=f"Task '{updated.title}' delayed", interpretation=interpretation, task=updated)
