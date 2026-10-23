from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def test_combined_app_serves_frontend_without_shadowing_api(client, tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<html><body>GhostComm Find frontend</body></html>")
    (frontend / "assets").mkdir()
    (frontend / "assets" / "main.js").write_text("document.title = 'GhostComm Find'")
    get_settings().frontend_dir = frontend
    with TestClient(create_app()) as combined:
        response = combined.get("/")
        assert response.status_code == 200
        assert "GhostComm Find frontend" in response.text
        assert "text/html" in response.headers["content-type"]
        assert combined.get("/assets/main.js").status_code == 200
        assert combined.get("/health").json() == {"status": "healthy"}
        assert combined.get("/api/v1/items").status_code == 401
        assert combined.get("/openapi.json").status_code == 200
        assert combined.get("/app/config.py").status_code == 404
        assert combined.get("/.env").status_code == 404


def test_standalone_backend_root_still_returns_status(client):
    assert client.get("/").json()["status"] == "online"
