from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = "iM뱅크 CLMS Demo"
    DEBUG: bool = True
    DATABASE_URL: str = f"sqlite:///{Path(__file__).parent.parent.parent.parent}/database/imbank_demo.db"

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]

    class Config:
        env_file = ".env"

settings = Settings()
