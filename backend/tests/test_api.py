from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest
from PIL import Image
from pydantic import SecretStr

from app.config import get_settings
from app.security import limiter
from tests.conftest import account, report


def test_authentication_and_password_protection(client):
    assert client.get("/api/v1/items").status_code == 401
    headers = account(client)
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["email"] == "alice@campus.example"
    assert "password_hash" not in me.json()
    assert (
        client.post(
            "/api/v1/auth/login",
            data={
                "username": "alice@campus.example",
                "password": "wrong",
            },
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "ALICE@campus.example",
                "name": "Alice",
                "password": "another-password-123",
            },
        ).status_code
        == 409
    )


def test_expired_and_tampered_tokens(client):
    headers = account(client)
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": headers["Authorization"] + "tampered",
            },
        ).status_code
        == 401
    )
    expired = jwt.encode(
        {
            "sub": "missing",
            "iss": "campus-lost-found",
            "aud": "campus-api",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        get_settings().jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {expired}",
            },
        ).status_code
        == 401
    )


def test_optional_campus_email_restriction(client):
    get_settings().campus_email_domains = "university.ac.ke"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "name": "Student",
            "password": "A-long-password-123",
        },
    )
    assert response.status_code == 422


def test_owner_permissions_search_and_resolution(client):
    owner, other = account(client), account(client, "bob")
    item = report(client, owner)
    path = f"/api/v1/items/{item['id']}"
    assert client.patch(path, headers=other, json={"status": "resolved"}).status_code == 403
    assert client.delete(path, headers=other).status_code == 403
    assert len(client.get("/api/v1/items?q=library", headers=owner).json()) == 1
    assert client.get("/api/v1/items?q=%25", headers=owner).json() == []
    assert client.patch(path, headers=owner, json={"title": None}).status_code == 422
    assert client.patch(path, headers=owner, json={"status": "resolved"}).status_code == 200
    assert client.get("/api/v1/items", headers=owner).json() == []
    assert client.post(path + "/matches", headers=owner).status_code == 409
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404


def test_image_upload_validation_and_access(client):
    owner, other = account(client), account(client, "bob")
    item = report(client, owner)
    path = f"/api/v1/items/{item['id']}/media"
    assert (
        client.post(
            path,
            headers=owner,
            files={
                "file": ("fake.png", b"not an image", "image/png"),
            },
        ).status_code
        == 415
    )
    image = BytesIO()
    Image.new("RGB", (10, 10), "red").save(image, "PNG")
    assert (
        client.post(
            path,
            headers=other,
            files={
                "file": ("photo.png", image.getvalue(), "image/png"),
            },
        ).status_code
        == 403
    )
    uploaded = client.post(
        path,
        headers=owner,
        files={
            "file": ("../../photo.png", image.getvalue(), "text/plain"),
        },
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["content_type"] == "image/jpeg"
    media_path = f"/api/v1/media/{uploaded.json()['id']}"
    assert client.get(media_path).status_code == 401
    assert client.get(media_path, headers=other).status_code == 200
    assert client.delete(media_path, headers=other).status_code == 403
    assert client.delete(media_path, headers=owner).status_code == 204
    assert list(get_settings().media_dir.iterdir()) == []


def test_oversized_upload(client):
    owner = account(client)
    item = report(client, owner)
    get_settings().max_upload_bytes = 1024
    response = client.post(
        f"/api/v1/items/{item['id']}/media",
        headers=owner,
        files={
            "file": ("huge.png", b"x" * 1025, "image/png"),
        },
    )
    assert response.status_code == 413


def test_private_conversations(client):
    owner, requester, stranger = account(client), account(client, "bob"), account(client, "eve")
    item = report(client, owner, "found")
    assert (
        client.post(
            "/api/v1/conversations",
            headers=owner,
            json={
                "item_id": item["id"],
            },
        ).status_code
        == 422
    )
    conversation = client.post(
        "/api/v1/conversations",
        headers=requester,
        json={
            "item_id": item["id"],
        },
    ).json()
    repeated = client.post(
        "/api/v1/conversations",
        headers=requester,
        json={
            "item_id": item["id"],
        },
    ).json()
    assert repeated["id"] == conversation["id"]
    path = f"/api/v1/conversations/{conversation['id']}/messages"
    assert (
        client.post(path, headers=requester, json={"body": "I think this is my bag"}).status_code
        == 201
    )
    assert (
        client.post(path, headers=owner, json={"body": "Describe the contents"}).status_code == 201
    )
    assert len(client.get(path, headers=owner).json()) == 2
    assert client.get(path, headers=stranger).status_code == 404
    assert client.post(path, headers=stranger, json={"body": "Read this"}).status_code == 404
    assert client.get("/api/v1/conversations", headers=stranger).json() == []
    assert client.delete(f"/api/v1/items/{item['id']}", headers=owner).status_code == 204
    assert client.get(path, headers=requester).status_code == 404


def test_ai_unconfigured(client):
    owner = account(client)
    item = report(client, owner)
    assert client.post(f"/api/v1/items/{item['id']}/matches", headers=owner).status_code == 503
    assert (
        client.post(
            "/api/v1/search/ai",
            headers=owner,
            json={
                "description": "Black laptop bag with a red zip",
            },
        ).status_code
        == 503
    )


def test_gemini_matching_filters_ids_and_persists(client, monkeypatch):
    owner, finder = account(client), account(client, "bob")
    lost = report(client, owner)
    found = report(client, finder, "found")
    picture = BytesIO()
    Image.new("RGB", (1000, 500), "black").save(picture, "PNG")
    assert (
        client.post(
            f"/api/v1/items/{lost['id']}/media",
            headers=owner,
            files={"file": ("bag.png", picture.getvalue(), "image/png")},
        ).status_code
        == 201
    )

    get_settings().gemini_api_key = SecretStr("test-api-key")
    sdk = MagicMock()
    sdk.models.generate_content.return_value = SimpleNamespace(
        text=(
            '{"matches": ['
            f'{{"target_id": "{found["id"]}", "score": 0.9, "reason": "Same red zip"}},'
            '{"target_id": "invented-id", "score": 1, "reason": "Ignore"}]}'
        )
    )
    factory = MagicMock()
    factory.return_value.__enter__.return_value = sdk
    monkeypatch.setattr("app.ai.genai.Client", factory)
    path = f"/api/v1/items/{lost['id']}/matches"
    response = client.post(path, headers=owner)
    assert response.status_code == 200, response.text
    assert [hit["target_id"] for hit in response.json()] == [found["id"]]
    parts = sdk.models.generate_content.call_args.kwargs["contents"]
    pictures = [part.inline_data for part in parts if part.inline_data is not None]
    assert len(pictures) == 1
    with Image.open(BytesIO(pictures[0].data)) as resized:
        assert max(resized.size) == 768
    assert client.get(path, headers=owner).json() == response.json()
    assert client.get(path, headers=finder).status_code == 403
    assert (
        client.patch(
            f"/api/v1/items/{found['id']}",
            headers=finder,
            json={
                "status": "resolved",
            },
        ).status_code
        == 200
    )
    assert client.get(path, headers=owner).json() == []


def test_gemini_failure_hides_provider_details(client, monkeypatch):
    owner, finder = account(client), account(client, "bob")
    lost = report(client, owner)
    report(client, finder, "found")
    get_settings().gemini_api_key = SecretStr("secret-provider-key")
    monkeypatch.setattr(
        "app.ai.genai.Client", MagicMock(side_effect=RuntimeError("secret-provider-key"))
    )
    response = client.post(f"/api/v1/items/{lost['id']}/matches", headers=owner)
    assert response.status_code == 502
    assert "secret-provider-key" not in response.text


@pytest.mark.parametrize(
    "response_text",
    [
        "not JSON",
        '{"matches":[{"target_id":"any","score":2,"reason":"Invalid score"}]}',
    ],
)
def test_invalid_gemini_response(client, monkeypatch, response_text):
    owner, finder = account(client), account(client, "bob")
    lost = report(client, owner)
    report(client, finder, "found")
    get_settings().gemini_api_key = SecretStr("test-key")
    factory = MagicMock()
    sdk = factory.return_value.__enter__.return_value
    sdk.models.generate_content.return_value = SimpleNamespace(text=response_text)
    monkeypatch.setattr("app.ai.genai.Client", factory)
    assert (
        client.post(
            f"/api/v1/items/{lost['id']}/matches",
            headers=owner,
        ).status_code
        == 502
    )


def test_rate_limit(client):
    for _ in range(10):
        limiter.check("auth:testclient", 10)
    assert (
        client.post(
            "/api/v1/auth/login",
            data={
                "username": "nobody@example.com",
                "password": "wrong",
            },
        ).status_code
        == 429
    )


def test_openapi_and_security_headers(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "/api/v1/search/ai" in response.json()["paths"]
