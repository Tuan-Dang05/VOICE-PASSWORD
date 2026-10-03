import os
import shutil
from pathlib import Path

os.environ["VOICE_DATABASE_URL"] = "sqlite:///./data/test_voice_password.db"
os.environ["VOICE_SECRET_KEY"] = "test-secret"
os.environ["VOICE_DATA_DIR"] = "data/test_runtime"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    Path("data/test_voice_password.db").unlink(missing_ok=True)
    shutil.rmtree("data/test_runtime", ignore_errors=True)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
