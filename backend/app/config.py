"""配置管理"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    APP_NAME = "AICC-Lite"
    VERSION = "3.0.0"
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"

    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/aicc_lite.db")

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    SECRET_KEY = os.getenv("SECRET_KEY", "aicc-lite-demo-secret-change-in-prod")

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    USE_LLM = bool(DEEPSEEK_API_KEY)


settings = Settings()
