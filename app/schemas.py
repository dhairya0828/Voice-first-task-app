from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import TaskEventType, TaskStatus


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=120)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskDelayRequest(BaseModel):
    days: Optional[int] = Field(default=None, ge=1, le=365)
    new_due_date: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    original_due_date: Optional[datetime]
    status: TaskStatus
    delayed_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class TaskEventResponse(BaseModel):
    id: int
    event_type: TaskEventType
    payload: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VoiceInterpretRequest(BaseModel):
    text: str = Field(min_length=2, max_length=800)


class VoiceExecuteRequest(VoiceInterpretRequest):
    force: bool = False


class VoiceInterpretation(BaseModel):
    original_text: str
    normalized_text: str
    action: Literal["create", "complete", "cancel", "delay"]
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)

    extracted_title: Optional[str] = None
    extracted_description: Optional[str] = None
    extracted_due_date: Optional[datetime] = None

    task_query: Optional[str] = None
    delay_days: Optional[int] = None
    target_due_date: Optional[datetime] = None

    follow_up_question: Optional[str] = None


class VoiceExecuteResponse(BaseModel):
    message: str
    interpretation: VoiceInterpretation
    task: Optional[TaskResponse] = None
    requires_confirmation: bool = False
    confirmation_reason: Optional[str] = None


class AnalyticsSummary(BaseModel):
    pending_tasks: int
    tasks_completed_on_time: int
    tasks_completed_late: int
    tasks_delayed: int
    tasks_cancelled: int


class AnalyticsDashboardResponse(BaseModel):
    summary: AnalyticsSummary
    status_distribution: dict[str, int]
    completion_trend: list[dict[str, Any]]
