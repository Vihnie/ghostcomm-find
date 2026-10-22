import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_engine
from app.init_db import main as init_db
from app.main import create_app
from app.security import limiter


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-" + "x" * 40)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("CAMPUS_EMAIL_DOMAINS", "")
    monkeypatch.setenv("APP_TIMEZONE", "Africa/Nairobi")
    get_settings.cache_clear()
    get_engine.cache_clear()
    limiter.events.clear()
    init_db()
    with TestClient(create_app()) as client:
        yield client
    get_engine().dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()


def account(client, name="alice"):
    email = f"{name}@campus.example"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "name": name,
            "password": "A-long-password-123",
        },
    )
    assert response.status_code == 201, response.text
    token = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": "A-long-password-123",
        },
    )
    assert token.status_code == 200, token.text
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def report(client, headers, kind="lost", **changes):
    payload = {
        "kind": kind,
        "title": "Black laptop bag",
        "description": "A black bag with a red zip",
        "category": "bags",
        "location": "Campus library",
        "occurred_at": "2026-10-19T09:00:00+03:00",
        **changes,
    }
    response = client.post("/api/v1/items", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()
