from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
  # API Settings
  API_V1_STR: str = "/api/v1"
  PROJECT_NAME: str = "Pharmacy Management System"

  # Database
  DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/pharmacy_db")

  # Security
  SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
  ALGORITHM: str = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

  # CORS
  CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

  # Email Settings
  SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
  SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
  SMTP_USER: str = os.getenv("SMTP_USER", "")
  SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

  # SMS Settings (Twilio)
  TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
  TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
  TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

  # AI/ML Settings
  OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
  GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

  # Redis for caching
  REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

  # File upload
  MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

  class Config:
    env_file = ".env"


settings = Settings()