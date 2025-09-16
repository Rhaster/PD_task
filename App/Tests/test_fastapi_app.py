""" Tests for the FastAPI application endpoints. """
import os
import io
from types import SimpleNamespace
from unittest.mock import Mock
import sys
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import main as appmod


client = TestClient(appmod.app)

sys.path.append(str(Path(__file__).parent.parent.parent)) 

def test_home_no_db_and_templatepatched(monkeypatch):
    """ Test the home page when no DB is connected and template rendering is patched."""
    monkeypatch.setattr(appmod, "npc_collection", None)

    
    def fake_template_response(template, ctx):
        ctx = {k: v for k, v in ctx.items() if k != "request"}
        return appmod.JSONResponse({"template": template, "ctx": ctx})

    monkeypatch.setattr(appmod, "templates", appmod.templates)  # ensure attribute exists
    monkeypatch.setattr(appmod.templates, "TemplateResponse", fake_template_response)

    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "ctx" in body

    assert body["ctx"]["npc_names"] == []


def test_get_npcs_reads_from_collection(monkeypatch):
    """ Test the /npcs endpoint reading from a fake NPC collection."""
    fake_docs = [{"name": "Alice"}, {"name": "Bob"}]

    class FakeCollection:
        def find(self, *args, **kwargs):
            return fake_docs

    monkeypatch.setattr(appmod, "npc_collection", FakeCollection())
    r = client.get("/npcs")
    assert r.status_code == 200
    assert r.json() == {"npc_names": ["Alice", "Bob"]}


def test_reset_chat_calls_context_cache_clear(monkeypatch):
    """ Test the /reset_chat endpoint calls context_cache.clear(). """
    cleared = {"called": False}

    class FakeCache:
        def clear(self):
            cleared["called"] = True

    monkeypatch.setattr(appmod, "context_cache", FakeCache())
    r = client.post("/reset_chat")
    assert r.status_code == 200
    assert cleared["called"] is True
    assert r.json() == {"status": "ok"}


def test_upload_story_saves_file(tmp_path):
    """ Test the /upload_story endpoint saves the uploaded file correctly."""
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
       
        os.makedirs("Data", exist_ok=True)
        file_content = b"# Story \n this is test."
        files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
        r = client.post("/upload_story", files=files)
        assert r.status_code == 200
        assert "File test.md saved  as fantasy.md" in r.json()["status"]
     
        assert (tmp_path / "Data" / "fantasy.md").exists()
        assert (tmp_path / "Data" / "fantasy.md").read_bytes() == file_content
    finally:
        os.chdir(cwd)


def test_run_faiss_success(monkeypatch):
    """ Test the /faiss/run_faiss endpoint with a successful build_index call."""
    result = {"chunks": 10, "index_path": "data/index.faiss", "meta_path": "data/index.faiss.meta.jsonl"}
    monkeypatch.setattr("Api.faiss_router.build_index", lambda **kwargs: result)
    r = client.post("/api/v1/faiss/run_faiss", json={"story_path": "Data/fantasy.md"})
    assert r.status_code == 200
    assert r.json() == result

def test_run_faiss_failure(monkeypatch):
    """ Test the /faiss/run_faiss endpoint handling a build_index exception."""
    def raise_err(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("Api.faiss_router.build_index", raise_err)
    r = client.post("/api/v1/faiss/run_faiss", json={"story_path": "App/Data/fantasy.md"})
    assert r.status_code == 500
    assert r.json()["error"] == "boom"


def test_chat_posts_to_local_qa(monkeypatch):
    """ Test the /chat endpoint posting to the local QA service."""
    class DummyResponse:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    class DummyAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, timeout=None):
            assert url.endswith("/api/v1/qa/qa")
            return DummyResponse({"answer": "ok"})

    monkeypatch.setattr(appmod, "httpx", appmod.httpx) 
    monkeypatch.setattr(appmod, "httpx", SimpleNamespace(AsyncClient=DummyAsyncClient))

    r = client.post("/api/v1/chat", data={"prompt": "Hello"})
    assert r.status_code == 200
    assert r.json() == {"answer": "ok"}
