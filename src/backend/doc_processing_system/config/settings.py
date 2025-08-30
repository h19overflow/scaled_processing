"""
Configuration management for the document processing system.
Loads environment variables from .env file and provides singleton access.
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Singleton configuration class that loads from environment variables."""
    
    # API Keys
    GEMINI_API_KEY: str
    OPENAI_API_KEY: str = ""
    WANDB_API_KEY: str = ""
    
    # Database Configuration
    POSTGRES_DSN: str
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: List[str] = ["localhost:9092"]
    
    # ChromaDB Configuration
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    
    # Prefect Configuration
    PREFECT_API_URL: str = "http://localhost:4200/api"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields to prevent validation errors


# Singleton instance
_settings_instance = None


def get_settings() -> Settings:
    """Get the singleton Settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings() -> None:
    """Reset the singleton instance (useful for testing or config changes)."""
    global _settings_instance
    _settings_instance = None