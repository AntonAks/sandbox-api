import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/sandbox_api")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DEMO_USER_EMAIL", "dispatcher@example.com")
os.environ.setdefault("DEMO_USER_PASSWORD", "dispatcher123")

from src.models.users import User  # noqa: E402


def test_user_columns():
    cols = {c.name for c in User.__table__.columns}
    assert cols == {"user_id", "email", "password_hash", "display_name", "created_at"}


def test_user_email_unique_index():
    indexes = {idx.name: idx for idx in User.__table__.indexes}
    assert "ix_users_email" in indexes
    idx = indexes["ix_users_email"]
    assert idx.unique
    col_names = [c.name for c in idx.columns]
    assert col_names == ["email"]
