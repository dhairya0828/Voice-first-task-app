from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import TaskStatus, User
from app.schemas import TaskCreateRequest, TaskDelayRequest, TaskResponse
from app.services.task_service import (
    cancel_task,
    complete_task,
    create_task,
    delay_task,
    get_task_for_user,
    list_tasks,
    update_task,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=180)
    description: Optional[str] = None
    due_date: Optional[datetime] = None


@router.get("", response_model=list[TaskResponse])
def get_tasks(
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    return list_tasks(db, current_user.id, status)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task_endpoint(
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    return create_task(
        db,
        current_user.id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        source="manual",
    )


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task_endpoint(
    task_id: int,
    payload: TaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = get_task_for_user(db, current_user.id, task_id)
    return update_task(
        db,
        task,
        current_user.id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )


@router.patch("/{task_id}/complete", response_model=TaskResponse)
def complete_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = get_task_for_user(db, current_user.id, task_id)
    return complete_task(db, task, current_user.id, source="manual")


@router.patch("/{task_id}/cancel", response_model=TaskResponse)
def cancel_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = get_task_for_user(db, current_user.id, task_id)
    return cancel_task(db, task, current_user.id, source="manual")


@router.patch("/{task_id}/delay", response_model=TaskResponse)
def delay_task_endpoint(
    task_id: int,
    payload: TaskDelayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = get_task_for_user(db, current_user.id, task_id)
    return delay_task(
        db,
        task,
        current_user.id,
        source="manual",
        days=payload.days,
        new_due_date=payload.new_due_date,
    )
