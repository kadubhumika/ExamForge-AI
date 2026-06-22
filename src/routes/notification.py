from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from src.database import get_db
from src.schemas import NotificationResponse
from src.services.auth_service import get_current_user
from src.models import Notification, User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def list_notifications(
        unread_only: bool = False,
        limit: int = 30,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)  # noqa: E712

    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return notifications


@router.put("/{notification_id}/read")
def mark_notification_read(
        notification_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.is_read = True
    db.commit()
    return {"status": "success"}


@router.put("/read-all")
def mark_all_read(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False  # noqa: E712
    ).update({"is_read": True})
    db.commit()
    return {"status": "success"}