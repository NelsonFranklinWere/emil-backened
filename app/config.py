from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database - try PostgreSQL first, fallback to SQLite
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./emilai.db")
    
    # ... rest of your config remains the same
    
    # JWT
    secret_key: str = os.getenv("SECRET_KEY")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    
    # File Upload
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", 10485760))
    
    # Email
    smtp_server: str = os.getenv("SMTP_SERVER")
    smtp_port: int = int(os.getenv("SMTP_PORT", 587))
    smtp_username: str = os.getenv("SMTP_USERNAME")
    smtp_password: str = os.getenv("SMTP_PASSWORD")
    
    # App URLs
    app_url: str = os.getenv("APP_URL", "http://localhost:8000")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # AI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()