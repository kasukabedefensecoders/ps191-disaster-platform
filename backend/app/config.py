from pydantic import field_validator
from pydantic_settings import BaseSettings


def _use_psycopg_driver(url: str) -> str:
    """Managed Postgres providers (Railway, Heroku, ...) hand out plain
    postgresql:// or postgres:// URLs. SQLAlchemy then defaults to psycopg2,
    which isn't installed (only psycopg[binary] is, per requirements.txt) —
    force the psycopg3 driver regardless of what scheme we're handed."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://app_user:app_user_pw@postgres:5432/ps191"
    migration_database_url: str = "postgresql+psycopg://ps191:ps191@postgres:5432/ps191"
    app_db_user: str = "app_user"
    app_db_password: str = "app_user_pw"
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "ps191minio"
    minio_secret_key: str = "ps191miniosecret"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    cors_allowed_origins: str = ""

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        return _use_psycopg_driver(v)

    class Config:
        env_file = ".env"


settings = Settings()
