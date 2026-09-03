from fastapi.testclient import TestClient

from matchlens.api import app, settings, store


def test_health_and_authenticated_job_creation(tmp_path):
    settings.data_dir=tmp_path; settings.api_key="test-secret"; settings.public_base_url=""
    store.path=tmp_path/"jobs.sqlite3"
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        denied=client.post("/v1/matches",json={"source":{"type":"url","ref":"https://example.com/game.mp4"},"target":{"player":"№7"}})
        assert denied.status_code == 401
        created=client.post("/v1/matches",headers={"x-api-key":"test-secret"},json={"source":{"type":"url","ref":"https://example.com/game.mp4"},"target":{"player":"№7"}})
        assert created.status_code == 200
        assert created.json()["status"] == "queued"
