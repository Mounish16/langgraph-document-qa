"""Shared fixtures: a scripted fake LLM and deterministic fake embeddings.

Nothing here needs Ollama or a network: every test runs the real graph, real agents,
real FAISS indexes and real prompts, with only the two model clients replaced.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage

from src import llm, retrievers
from src.config import settings

AGENT_NAMES = {"hld": "Agent 1", "techreq": "Agent 2", "lld": "Agent 3"}


class FakeEmbeddings(Embeddings):
    """Bag-of-words hashing embeddings: deterministic, offline, good enough for FAISS."""

    DIM = 128

    def _vec(self, text: str) -> list[float]:
        v = np.zeros(self.DIM)
        for word in text.lower().split():
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.DIM] += 1.0
        norm = np.linalg.norm(v)
        return (v / norm if norm else v).tolist()

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeLLM:
    """Replies according to which prompt it receives, and records every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []   # (system, user)
        self.route_to = "hld"                    # what the router replies
        self.not_found: set[str] = set()         # collections whose agent says NOT_FOUND

    def invoke(self, messages):
        system, user = messages[0].content, messages[-1].content
        self.calls.append((system, user))

        if "route a question" in system:
            return AIMessage(content=self.route_to)
        if "senior design reviewer" in system:
            return AIMessage(content="## Verdict\nAligned\n## Traceability\n| FR-4 | s1 | met |")
        if "authoring a new Low Level Design" in system:
            return AIMessage(content="# DOC 3.4 - Low Level Design\n\n## Scope\nGenerated.")
        for collection, name in AGENT_NAMES.items():
            if system.startswith(f"You are {name}"):
                if collection in self.not_found:
                    return AIMessage(content="NOT_FOUND")
                return AIMessage(content=f"Answer from {collection}")
        raise AssertionError(f"unexpected prompt: {system[:80]}")


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    """Point indexes/outputs at a temp dir and swap in the fake model clients."""
    fake = FakeLLM()
    monkeypatch.setattr(settings, "index_dir", tmp_path / "faiss_index")
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")
    settings.index_dir.mkdir()
    settings.output_dir.mkdir()
    monkeypatch.setattr(llm, "get_llm", lambda: fake)
    monkeypatch.setattr(llm, "get_embeddings", lambda: FakeEmbeddings())
    retrievers.load_store.cache_clear()
    yield fake
    retrievers.load_store.cache_clear()


@pytest.fixture
def fake_llm(sandbox) -> FakeLLM:
    return sandbox


@pytest.fixture
def indexed(sandbox):
    """Build the real FAISS indexes (with fake embeddings) from the bundled documents."""
    from src import ingest

    ingest.build_all()
    retrievers.load_store.cache_clear()
    return sandbox
