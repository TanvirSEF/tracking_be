from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Centralized application settings.
    These values are automatically loaded from environment variables or .env file.
    """
    DATABASE_URL: str = "postgresql://postgres:password@localhost/affiliate_db"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_REGISTRATION_LINK: str = "ADMIN-SECURE-LINK-2024"
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create a single instance to be imported throughout the application
settings = Settings()

