from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas import UserCreate, UserLogin, GoogleLoginRequest, ProfileUpdate
from src.services.auth_service import AuthService, get_current_user
from src.services.notification_service import NotificationService
from src.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_teacher(payload: UserCreate, db: Session = Depends(get_db)):
    user = AuthService.register_teacher(payload, db)
    return {"message": "Teacher profile registered successfully", "user_id": str(user.id)}


@router.post("/login")
def login_teacher(payload: UserLogin, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return AuthService.login_with_password(payload, background_tasks, db)


@router.post("/google")
def login_google(payload: GoogleLoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return AuthService.login_with_google(payload.id_token, background_tasks, db)


@router.put("/profile/update", status_code=status.HTTP_200_OK)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Secured: the user being updated comes from the JWT, never from a client-supplied id."""
    theme_changed = False
    from src.models import UserSetting
    existing_setting = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if existing_setting and existing_setting.theme != payload.theme:
        theme_changed = True

    result = AuthService.update_profile(current_user, payload.name, payload.theme, db)

    NotificationService.profile_updated(db, current_user.id)
    if theme_changed:
        NotificationService.theme_changed(db, current_user.id, payload.theme)

    return result