import smtplib
from email.mime.text import MIMEText
from fastapi import HTTPException, status, BackgroundTasks
from jose import jwt
from passlib.context import CryptContext
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.orm import Session
from src.config import settings
from src.models import User, School, Class, UserSetting
from src.schemas import UserCreate, UserLogin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def send_welcome_email(email: str, name: str):
        """Dispatched asynchronously via BackgroundTasks to eliminate web-route latency"""
        try:
            msg = MIMEText(
                f"Hello {name},\n\nYour login to ExamForge-AI was successful! Welcome back to your dashboard.")
            msg['Subject'] = f"🔄 Secure Login Alert - {settings.APP_NAME}"
            msg['From'] = "security@examforge.ai"
            msg['To'] = email

            # For local testing, prints to console. Plug in SMTP server details when ready:
            print(f"[SMTP SEND] Outbound email dispatched successfully to: {email}")
        except Exception as e:
            print(f"[SMTP ERROR] Failed to deliver alert: {str(e)}")

    @classmethod
    def register_teacher(cls, payload: UserCreate, db: Session) -> User:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        school = db.query(School).filter(
            School.name == payload.school_name
        ).first()

        if not school:
            school = School(name=payload.school_name)
            db.add(school)
            db.commit()
            db.refresh(school)

        new_user = User(
            name=payload.name,
            email=payload.email,
            password_hash=cls.get_password_hash(payload.password),
            school_id=school.id
        )
        db.add(new_user)
        db.flush()

        db.add(UserSetting(user_id=new_user.id, theme="white"))
        db.commit()
        return new_user

    @classmethod
    def login_with_password(cls, payload: UserLogin, background_tasks: BackgroundTasks, db: Session) -> str:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user or not cls.verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid system credentials")

        background_tasks.add_task(cls.send_welcome_email, user.email, user.name)
        return cls.create_access_token({"user_id": str(user.id), "school_id": str(user.school_id)})

    @classmethod
    def login_with_google(cls, token: str, background_tasks: BackgroundTasks, db: Session) -> str:
        try:
            # 🌟 FIXED: Added complete token verification logic so email and name are properly defined
            id_info = google_id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                "GOOGLE_CLIENT_ID"  # Replace with your real Google Client ID in production
            )
            email = id_info["email"]
            name = id_info["name"]
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google authentication failed")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            default_school = db.query(School).first()
            if not default_school:
                default_school = School(name="Default Google School")
                db.add(default_school)
                db.flush()

            user = User(
                name=name,
                email=email,
                password_hash="🚨_OAUTH_PROV_GOOGLE_SECURE_NULL_KEY",
                school_id=default_school.id
            )
            db.add(user)
            db.flush()
            db.add(UserSetting(user_id=user.id, theme="white"))
            db.commit()

        background_tasks.add_task(cls.send_welcome_email, user.email, user.name)
        return cls.create_access_token({"user_id": str(user.id), "school_id": str(user.school_id)})

    @staticmethod
    def update_profile(user_id: str, name: str, theme: str, db: Session):
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.name = name
            if user.settings:
                user.settings.theme = theme
            db.commit()
        return {"status": "success"}
