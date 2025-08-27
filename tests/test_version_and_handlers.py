from fastapi.testclient import TestClient

from main import app

# ここがポイント：サーバ例外をレスポンスにする
client = TestClient(app, raise_server_exceptions=False)


def test_version_endpoint() -> None:
    r = client.get("/version")
    assert r.status_code == 200
    data = r.json()
    for k in ("version", "git_sha", "started_at", "python"):
        assert k in data
    assert "T" in data["started_at"] and ("+" in data["started_at"] or "Z" in data["started_at"])


def test_internal_server_error_handler() -> None:
    r = client.get("/__error")
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal Server Error"}
