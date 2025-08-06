from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name: str = os.getenv("DATABASE_NAME", "whatsapp_automation")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # WhatsApp Node.js server
    whatsapp_server_url: str = os.getenv("WHATSAPP_SERVER_URL", "http://localhost:3000")
    
    # Email Settings
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    
    # File upload
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB default
    upload_dir: str = "uploads"
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Message Queue Settings
    max_queue_size: int = int(os.getenv("MAX_QUEUE_SIZE", "1000"))
    message_retry_attempts: int = int(os.getenv("MESSAGE_RETRY_ATTEMPTS", "3"))
    message_timeout: int = int(os.getenv("MESSAGE_TIMEOUT", "300"))  # 5 minutes
    
    # Excel Export Settings
    export_interval_minutes: int = int(os.getenv("EXPORT_INTERVAL_MINUTES", "15"))
    export_cleanup_days: int = int(os.getenv("EXPORT_CLEANUP_DAYS", "7"))
    
    class Config:
        env_file = ".env"

settings = Settings()