from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
from pathlib import Path

# Get the directory containing this config file
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = Field(default="AI Web Scraper API", description="Application name")
    VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Environment: development or production")
    DEBUG: bool = Field(default=False, description="Debug mode")
    VERBOSE: int = Field(default=1, description="Verbosity level")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # Security
    # SECRET_KEY: Optional[str] = Field(default="", description="Secret key for security")

    # CORS Configuration
    ALLOWED_HOSTS: str = Field(default="localhost,127.0.0.1,0.0.0.0", description="Allowed hosts")
    CORS_ORIGINS: list = Field(
        default=["http://localhost:3000", "http://localhost:8080", "http://localhost:8501"],
        description="Allowed CORS origins"
    )

    # Stagehand/Browserbase Configuration
    STAGEHAND_ENV: str = Field(default="BROWSERBASE", description="Stagehand environment: BROWSERBASE or LOCAL")
    BROWSERBASE_API_KEY: Optional[str] = Field(default=None, description="Browserbase API key")
    BROWSERBASE_PROJECT_ID: Optional[str] = Field(default=None, description="Browserbase project ID")

    # Stagehand Settings
    DOM_SETTLE_TIMEOUT_MS: int = Field(default=30000, description="DOM settle timeout in milliseconds")
    SELF_HEAL: bool = Field(default=True, description="Enable self-healing functionality")
    HEADLESS: bool = Field(default=True, description="Run browser in headless mode")

    # Job Processing (legacy, kept for compatibility)
    MAX_CONCURRENT_JOBS: int = Field(default=3, description="Maximum concurrent jobs")
    JOB_TIMEOUT_MINUTES: int = Field(default=15, description="Job timeout in minutes")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # AI Model Configuration
    MODEL_API_KEY: Optional[str] = Field(default=None, description="Model API key")
    MODEL_NAME: str = Field(default="", description="LLM model name")
    MODEL_BASE_URL: str = Field(default="", description="Model base URL")


    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='allow'
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Global settings instance
settings = get_settings()
