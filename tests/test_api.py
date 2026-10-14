import pytest
from fastapi.testclient import TestClient

from src import api
from src.config import settings


@pytest.fixture
def client(indexed, monkeypatch):
    monkeypatch.setattr(api, "_ollama_up", lambda: True)
    return TestClient(api.app)


def test_home_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "LangGraph Document Q&amp;A" in r.text


def test_status_reports_collections_and_indexes(client):
    body = client.get("/api/status").json()
    assert body["ollama_up"] is True
    assert {c["collection"] for c in body["collections"]} == {"hld", "techreq", "lld"}
    assert all(c["index_built"] for c in body["collections"])


def test_ask_returns_answer_and_download_links(client):
    r = client.post("/api/ask", json={"question": "Generate LLD 3.4"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "q2" and body["answer"].startswith("# DOC 3.4")
    name = body["files"]["md"]
    dl = client.get(f"/api/download/{name}")
    assert dl.status_code == 200 and dl.headers["content-type"].startswith("text/markdown")


def test_ask_rejects_an_empty_question(client):
    assert client.post("/api/ask", json={"question": "  "}).status_code == 400


def test_download_unknown_file_is_404(client):
    assert client.get("/api/download/nope.pdf").status_code == 404


def test_download_cannot_escape_the_outputs_folder(client, tmp_path):
    (tmp_path / "secret.txt").write_text("nope")
    assert client.get("/api/download/..%2Fsecret.txt").status_code == 404
    assert client.get("/api/download/%2e%2e/secret.txt").status_code == 404
    assert (settings.output_dir.parent / "secret.txt").exists()


def test_ask_builds_missing_indexes_on_first_use(sandbox, monkeypatch):
    monkeypatch.setattr(api, "_ollama_up", lambda: True)
    client = TestClient(api.app)
    assert not any((settings.index_dir / c).exists() for c in ("hld", "techreq", "lld"))
    r = client.post("/api/ask", json={"question": "What are the goals in the HLD?"})
    assert r.status_code == 200
    assert (settings.index_dir / "hld" / "index.faiss").exists()
