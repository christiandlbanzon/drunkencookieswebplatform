"""
Centralized configuration for the Drunken Cookies Operations Platform.
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database — supports both direct URL and Cloud SQL socket
    DB_URL: str = "postgresql://postgres:postgres@localhost:5432/drunken_cookies"
    CLOUD_SQL_CONNECTION_NAME: str = ""  # e.g. "project:region:instance"

    # JWT Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480  # 8 hours

    # Google Sheets (dual-write during transition)
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "service_account.json"
    SALES_SHEET_ID: str = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
    MALL_PARS_SHEET_ID: str = "1C5_N8oHds9Xw9pqN5PptGAVHJ2WeKrh35PCiejusl88"
    DISPATCH_PARS_SHEET_ID: str = "1XC9o3iGhv2YWAXZqnDwz0bxA1N4kJKkn_fswiz7X6ek"
    MORNING_PARS_SHEET_ID: str = "1BbZc3DYa3r0aCR2jiwm6ecs7cs7v4IRO39nHFIYR1oc"

    # Clover API
    CLOVER_API_BASE_URL: str = "https://api.clover.com"
    CLOVER_API_TIMEOUT: int = 30
    CLOVER_MAX_RETRIES: int = 3

    # Shopify API
    SHOPIFY_STORE_NAME: str = ""
    SHOPIFY_API_TOKEN: str = ""
    SHOPIFY_API_VERSION: str = "2023-01"

    # App
    TIMEZONE: str = "America/Puerto_Rico"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    DUAL_WRITE_ENABLED: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
