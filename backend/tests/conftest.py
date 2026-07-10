import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

TEST_DB = Path(__file__).parent / "test_devops_review.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["DEMO_MODE"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-bytes"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    if TEST_DB.exists():
        TEST_DB.unlink()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_token(client):
    response = client.post(
        "/api/auth/login", json={"email": "admin@demo.com", "password": "demo1234"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def auditor_headers(client):
    response = client.post(
        "/api/auth/login", json={"email": "auditor@demo.com", "password": "demo1234"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
