from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.auth_service import get_current_user
from src.services.analytics_service import AnalyticsService
from src.models import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/school")
def get_school_analytics(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """School-wide analytics — all teachers + their assignment performance."""
    return AnalyticsService.get_school_analytics(str(current_user.school_id), db)


@router.get("/teacher")
def get_my_analytics(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Current teacher's personal analytics."""
    return AnalyticsService.get_teacher_analytics(str(current_user.id), db)