from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    APP_NAME: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    SMTP_SENDER_EMAIL: str
    SMTP_SENDER_PASSWORD: str

    class Config:
        env_file = ".env"
        extra = "ignore"  # Skips extra raw Postgres/Redis parameters safely

settings = Settings()
