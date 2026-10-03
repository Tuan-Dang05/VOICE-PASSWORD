import sqlite3

from sqlalchemy import create_engine, inspect

from app.database import Base, upgrade_sqlite_schema


def test_existing_sqlite_database_gets_dtw_columns_without_losing_attempts(tmp_path):
    database = tmp_path / "old.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE authentication_attempts (id INTEGER PRIMARY KEY, reason VARCHAR(80))")
        connection.execute("INSERT INTO authentication_attempts (id, reason) VALUES (7, 'speaker_mismatch')")
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    try:
        Base.metadata.create_all(bind=engine)
        upgrade_sqlite_schema(engine)
        upgrade_sqlite_schema(engine)
        with engine.connect() as connection:
            columns = {column["name"] for column in inspect(connection).get_columns("authentication_attempts")}
            assert {"dtw_score", "dtw_threshold", "speaker_score"} <= columns
            assert connection.exec_driver_sql("SELECT reason FROM authentication_attempts WHERE id = 7").scalar_one() == "speaker_mismatch"
            assert "voice_command_templates" in inspect(connection).get_table_names()
            assert "speaker_threshold" in {column["name"] for column in inspect(connection).get_columns("voice_passwords")}
    finally:
        engine.dispose()
