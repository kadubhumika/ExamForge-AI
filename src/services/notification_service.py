from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.models import Notification


class NotificationService:
    @staticmethod
    def create(
        db: Session,
        user_id,
        type: str,
        title: str,
        message: Optional[str] = None,
        related_id: Optional[UUID] = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            related_id=related_id,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def assignment_created(db: Session, user_id, assignment_id, title: str):
        return NotificationService.create(
            db, user_id, "ASSIGNMENT_CREATED",
            "Assignment created",
            f'"{title}" was created and is being generated.',
            assignment_id,
        )

    @staticmethod
    def assignment_ready(db: Session, user_id, assignment_id, title: str):
        return NotificationService.create(
            db, user_id, "ASSIGNMENT_READY",
            "Assignment ready",
            f'"{title}" has finished generating and is ready to download.',
            assignment_id,
        )

    @staticmethod
    def assignment_failed(db: Session, user_id, assignment_id, title: str, reason: str = ""):
        return NotificationService.create(
            db, user_id, "ASSIGNMENT_FAILED",
            "Assignment generation failed",
            f'"{title}" failed to generate. {reason}'.strip(),
            assignment_id,
        )

    @staticmethod
    def assignment_deleted(db: Session, user_id, assignment_id, title: str):
        return NotificationService.create(
            db, user_id, "ASSIGNMENT_DELETED",
            "Assignment deleted",
            f'"{title}" was deleted.',
            assignment_id,
        )

    @staticmethod
    def profile_updated(db: Session, user_id):
        return NotificationService.create(
            db, user_id, "PROFILE_UPDATED",
            "Profile updated",
            "Your profile details were updated.",
        )

    @staticmethod
    def theme_changed(db: Session, user_id, theme: str):
        return NotificationService.create(
            db, user_id, "THEME_CHANGED",
            "Theme changed",
            f"Your interface theme was switched to {theme} mode.",
        )