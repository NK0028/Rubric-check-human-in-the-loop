"""Small, dependency-free runtime configuration for local and production use."""

import os


def _csv_setting(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _bool_setting(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


environment = os.getenv("APP_ENV", "development").strip().lower()
cors_origins = _csv_setting("CORS_ORIGINS", "http://localhost:3000")
allowed_hosts = _csv_setting("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
cookie_secure = _bool_setting("COOKIE_SECURE", environment == "production")
database_url = os.getenv("DATABASE_URL", "").strip()

if environment == "production" and "*" in cors_origins:
    raise RuntimeError("CORS_ORIGINS must list explicit HTTPS origins in production.")
if environment == "production" and not database_url.startswith("postgresql+psycopg://"):
    raise RuntimeError("Production requires DATABASE_URL using postgresql+psycopg://.")
if environment == "production" and not cookie_secure:
    raise RuntimeError("COOKIE_SECURE must be true in production.")
