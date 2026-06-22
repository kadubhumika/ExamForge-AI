import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.orm import Session

from src.config import settings
from src.models import User, School, UserSetting
from src.schemas import UserCreate, UserLogin
from src.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


class AuthService:
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token"
            )

    @staticmethod
    def send_welcome_email(email: str, name: str):
        """Dispatched asynchronously via BackgroundTasks to eliminate web-route latency"""
        try:
            if not settings.SMTP_SENDER_EMAIL or not settings.SMTP_SENDER_PASSWORD:
                print(f"[SMTP SKIP] No SMTP credentials configured, skipping email to {email}")
                return

            msg = MIMEText(
                f"Hello {name},\n\nYour login to {settings.APP_NAME} was successful! Welcome back to your dashboard."
            )
            msg['Subject'] = f"Secure Login Alert - {settings.APP_NAME}"
            msg['From'] = settings.SMTP_SENDER_EMAIL
            msg['To'] = email

            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_SENDER_EMAIL, settings.SMTP_SENDER_PASSWORD)
                server.sendmail(settings.SMTP_SENDER_EMAIL, email, msg.as_string())

            print(f"[SMTP SEND] Email dispatched successfully to: {email}")
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

        db.add(UserSetting(user_id=new_user.id, theme="light"))
        db.commit()
        return new_user

    @classmethod
    def login_with_password(cls, payload: UserLogin, background_tasks: BackgroundTasks, db: Session):
        user = db.query(User).filter(User.email == payload.email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if not cls.verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid password")

        background_tasks.add_task(cls.send_welcome_email, user.email, user.name)

        school = db.query(School).filter(School.id == user.school_id).first()
        setting = db.query(UserSetting).filter(
            UserSetting.user_id == user.id
        ).first()

        return {
            "access_token": cls.create_access_token({"user_id": str(user.id), "school_id": str(user.school_id)}),
            "token_type": "bearer",
            "user_id": str(user.id),
            "school_id": str(user.school_id),
            "school_name": school.name if school else "Unknown Institution",
            "user_name": user.name,
            "email": user.email,
            "theme": setting.theme if setting else "light"
        }

    @classmethod
    def login_with_google(cls, token: str, background_tasks: BackgroundTasks, db: Session):
        try:
            id_info = google_id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
                clock_skew_in_seconds=10
            )
            email = id_info["email"]
            name = id_info["name"]
        except Exception as e:
            print(e)
            raise HTTPException(status_code=401, detail=str(e))

        user = db.query(User).filter(User.email == email).first()
        if not user:
            default_school = db.query(School).first()
            if not default_school:
                default_school = School(name="Bokaro Steel City School")
                db.add(default_school)
                db.flush()

            user = User(
                name=name,
                email=email,
                password_hash="OAUTH_GOOGLE_NO_PASSWORD",
                school_id=default_school.id
            )
            db.add(user)
            db.flush()
            db.add(UserSetting(user_id=user.id, theme="light"))
            db.commit()
        else:
            if not user.name or not user.name.strip():
                user.name = name
                db.commit()

        background_tasks.add_task(cls.send_welcome_email, user.email, user.name)

        school = db.query(School).filter(School.id == user.school_id).first()
        setting = db.query(UserSetting).filter(
            UserSetting.user_id == user.id
        ).first()

        return {
            "access_token": cls.create_access_token({"user_id": str(user.id), "school_id": str(user.school_id)}),
            "token_type": "bearer",
            "user_id": str(user.id),
            "school_id": str(user.school_id),
            "school_name": school.name if school else "Unknown Institution",
            "user_name": user.name,
            "email": user.email,
            "theme": setting.theme if setting else "light"
        }

    @staticmethod
    def update_profile(user: User, name: str, theme: str, db: Session):
        user.name = name
        setting = db.query(UserSetting).filter(
            UserSetting.user_id == user.id
        ).first()

        if setting:
            setting.theme = theme
        else:
            setting = UserSetting(user_id=user.id, theme=theme)
            db.add(setting)

        db.commit()
        db.refresh(user)

        return {
            "status": "success",
            "user_name": user.name,
            "theme": setting.theme
        }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Real auth dependency: decodes the JWT issued at login and loads the User row.
    Use this everywhere instead of the old hardcoded mock."""
    payload = AuthService.decode_access_token(credentials.credentials)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user