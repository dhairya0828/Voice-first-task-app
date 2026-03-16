from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import AnalyticsDashboardResponse
from app.services.analytics import build_dashboard

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
def analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsDashboardResponse:
    data = build_dashboard(db, current_user.id)
    return AnalyticsDashboardResponse(**data)
