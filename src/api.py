"""FastAPI backend for the test frontend.

Run:  uvicorn src.api:app --host 0.0.0.0 --port 8000
Open: http://localhost:8000

Blocking work (ingest / evaluate) is offloaded to a worker thread with
asyncio.to_thread so the event loop stays responsive.
"""
from __future__ import annotations

import asyncio
import urllib.request
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import COLLECTIONS, settings

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

app = FastAPI(title="LangGraph HLD/TechReq/LLD - ask")


class AskBody(BaseModel):
    question: str


def _ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{settings.ollama_base_url}/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _collection_status(c: str) -> dict:
    return {
        "collection": c,
        "folder": f"data/{COLLECTIONS[c]}",
        "index_built": (settings.index_dir / c).exists(),
    }


def _ensure_indexed() -> None:
    """Build any missing FAISS indexes (idempotent) so the first ask just works."""
    from . import ingest as ingest_mod

    if any(not (settings.index_dir / c).exists() for c in COLLECTIONS):
        ingest_mod.build_all()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(FRONTEND))


@app.get("/api/status")
def status() -> dict:
    return {
        "ollama_up": _ollama_up(),
        "ollama_url": settings.ollama_base_url,
        "llm_model": settings.llm_model,
        "embed_model": settings.embed_model,
        "collections": [_collection_status(c) for c in COLLECTIONS],
    }


@app.post("/api/ingest")
async def ingest() -> dict:
    from . import ingest as ingest_mod

    await asyncio.to_thread(ingest_mod.build_all)
    return {"ok": True, "collections": [_collection_status(c) for c in COLLECTIONS]}


@app.post("/api/ask")
async def ask(body: AskBody) -> dict:
    """Ask a question: (auto-)build indexes, answer it, export to pdf/docx/md."""
    from . import evaluation

    question = (body.question or "").strip()
    if not question:
        raise HTTPException(400, "question is empty")
    try:
        await asyncio.to_thread(_ensure_indexed)
        res = await asyncio.to_thread(evaluation.answer_question, question)
        return res
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


_MEDIA = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
}


@app.get("/api/download/{name}")
def download(name: str) -> FileResponse:
    safe = Path(name).name
    path = settings.output_dir / safe
    if not path.exists() or not path.is_file():
        raise HTTPException(404, f"{safe} not found")
    media = _MEDIA.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(path), filename=safe, media_type=media)
