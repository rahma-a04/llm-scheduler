"""Application configuration and settings."""

import os
from dataclasses import dataclass
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment."""

    # API Keys
    openai_api_key: str

    # Google Calendar
    google_credentials_path: str = "../credentials.json"

    # Scheduling defaults
    default_scheduler: str = "llm"  # or "baseline"
    default_buffer_minutes: int = 15
    default_max_daily_hours: int = 6

    # LLM settings
    llm_model: str = "gpt-4o"


@lru_cache()
def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        google_credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "../credentials.json"),
        default_scheduler=os.getenv("DEFAULT_SCHEDULER", "llm"),
        default_buffer_minutes=int(os.getenv("DEFAULT_BUFFER_MINUTES", "15")),
        default_max_daily_hours=int(os.getenv("DEFAULT_MAX_DAILY_HOURS", "6")),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o")
    )
