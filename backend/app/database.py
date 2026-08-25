import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


default_database_path = Path(__file__).resolve().parents[1] / "rubricheck.db"
database_url = os.getenv("DATABASE_URL", f"sqlite:///{default_database_path}")
engine_options = {"connect_args": {"check_same_thread": False}} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def migrate_legacy_schema() -> None:
    """Apply additive migrations needed by the local SQLite prototype."""
    inspector = inspect(engine)
    if "courses" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("courses")}
        if "owner_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE courses ADD COLUMN owner_id INTEGER"))
    if "evaluation_criteria" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("evaluation_criteria")}
        if "feedback_suggestion" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE evaluation_criteria ADD COLUMN feedback_suggestion TEXT NOT NULL DEFAULT ''"))
