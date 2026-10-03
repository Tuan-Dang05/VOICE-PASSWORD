from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def upgrade_sqlite_schema(database_engine=engine) -> None:
    if database_engine.dialect.name != "sqlite":
        return
    with database_engine.begin() as connection:
        profile_columns = {column["name"] for column in inspect(connection).get_columns("voice_passwords")}
        if "speaker_threshold" not in profile_columns:
            connection.exec_driver_sql("ALTER TABLE voice_passwords ADD COLUMN speaker_threshold FLOAT")
        columns = {column["name"] for column in inspect(connection).get_columns("authentication_attempts")}
        if "speaker_score" not in columns:
            connection.exec_driver_sql("ALTER TABLE authentication_attempts ADD COLUMN speaker_score FLOAT")
        if "dtw_score" not in columns:
            connection.exec_driver_sql("ALTER TABLE authentication_attempts ADD COLUMN dtw_score FLOAT")
        if "dtw_threshold" not in columns:
            connection.exec_driver_sql("ALTER TABLE authentication_attempts ADD COLUMN dtw_threshold FLOAT")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
