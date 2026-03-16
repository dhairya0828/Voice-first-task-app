from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import Task, TaskStatus


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def build_dashboard(db: Session, user_id: int, trend_days: int = 14) -> dict:
    now = datetime.utcnow()
    tasks = db.query(Task).filter(Task.user_id == user_id).all()

    pending_tasks = sum(task.status == TaskStatus.PENDING for task in tasks)
    tasks_completed_on_time = sum(
        task.status == TaskStatus.COMPLETED
        and _normalize_datetime(task.due_date) is not None
        and _normalize_datetime(task.completed_at) is not None
        and _normalize_datetime(task.completed_at) <= _normalize_datetime(task.due_date)
        for task in tasks
    )
    tasks_completed_late = sum(
        task.status == TaskStatus.COMPLETED
        and _normalize_datetime(task.due_date) is not None
        and _normalize_datetime(task.completed_at) is not None
        and _normalize_datetime(task.completed_at) > _normalize_datetime(task.due_date)
        for task in tasks
    )
    tasks_delayed = sum(task.delayed_count > 0 for task in tasks)
    tasks_cancelled = sum(task.status == TaskStatus.CANCELLED for task in tasks)

    status_distribution = {
        "pending": pending_tasks,
        "completed": sum(task.status == TaskStatus.COMPLETED for task in tasks),
        "cancelled": tasks_cancelled,
        "overdue_pending": sum(
            task.status == TaskStatus.PENDING
            and _normalize_datetime(task.due_date) is not None
            and _normalize_datetime(task.due_date) < now
            for task in tasks
        ),
    }

    completion_trend: List[Dict[str, Any]] = []
    for offset in reversed(range(trend_days)):
        day = (now - timedelta(days=offset)).date()
        count = sum(
            _normalize_datetime(task.completed_at) is not None and _normalize_datetime(task.completed_at).date() == day
            for task in tasks
        )
        completion_trend.append({"date": day.isoformat(), "completed": count})

    return {
        "summary": {
            "pending_tasks": pending_tasks,
            "tasks_completed_on_time": tasks_completed_on_time,
            "tasks_completed_late": tasks_completed_late,
            "tasks_delayed": tasks_delayed,
            "tasks_cancelled": tasks_cancelled,
        },
        "status_distribution": status_distribution,
        "completion_trend": completion_trend,
    }
