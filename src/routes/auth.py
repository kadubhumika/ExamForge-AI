from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas import UserCreate, UserLogin, Token, UserResponse
from src.services.auth_service import AuthService
from src.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_teacher(payload: UserCreate, db: Session = Depends(get_db)):
    user = AuthService.register_teacher(payload, db)
    return {"message": "Teacher profile registered successfully", "user_id": str(user.id)}

@router.post("/login", response_model=Token)
def login_teacher(payload: UserLogin, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    token = AuthService.login_with_password(payload, background_tasks, db)
    return {"access_token": token, "token_type": "bearer"}

from pydantic import BaseModel

class GoogleLoginRequest(BaseModel):
    id_token: str

@router.post("/google", response_model=Token)
def login_google(
    payload: GoogleLoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    token = AuthService.login_with_google(payload.id_token, background_tasks, db)
    return {"access_token": token, "token_type": "bearer"}


@router.put("/profile/update", status_code=status.HTTP_200_OK)
def update_profile(user_id: str, name: str, theme: str, db: Session = Depends(get_db)):
    # Connects safely to the profile and theme service logic
    return AuthService.update_profile(user_id, name, theme, db)
