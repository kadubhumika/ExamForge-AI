from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days, since login has "keep active 30 days" UI

    APP_NAME: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    SMTP_SENDER_EMAIL: str
    SMTP_SENDER_PASSWORD: str

    # AI generation
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # File storage
    STORAGE_DIR: str = "storage"
    MAX_UPLOAD_MB: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"  # Skips extra raw Postgres/Redis parameters safely


settings = Settings()