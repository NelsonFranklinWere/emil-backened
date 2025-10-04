from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Settings(BaseSettings):
    # -------------------------------------------------
    # Database: Use PostgreSQL by default, fallback to SQLite
    # -------------------------------------------------
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://emil_user:StrongP@ssw0rd@localhost:5432/emil_ai"
    )

    # -------------------------------------------------
    # JWT / Security
    # -------------------------------------------------
    secret_key: str = os.getenv("SECRET_KEY", "supersecretkey")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    # -------------------------------------------------
    # File Uploads
    # -------------------------------------------------
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10 MB

    # -------------------------------------------------
    # Email (SMTP)
    # -------------------------------------------------
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", 587))
    smtp_username: Optional[str] = os.getenv("SMTP_USERNAME")
    smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")

    # -------------------------------------------------
    # App URLs
    # -------------------------------------------------
    app_url: str = os.getenv("APP_URL", "http://localhost:8000")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # -------------------------------------------------
    # AI Services
    # -------------------------------------------------
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    # -------------------------------------------------
    # Environment
    # -------------------------------------------------
    environment: str = os.getenv("ENVIRONMENT", "development")


settings = Settings()
