"""Load persisted FAISS indexes and expose helpers to fetch context."""
from __future__ import annotations

from functools import lru_cache

from langchain_community.vectorstores import FAISS

from . import llm
from .config import settings


@lru_cache(maxsize=8)
def load_store(collection: str) -> FAISS:
    path = settings.index_dir / collection
    if not path.exists():
        raise FileNotFoundError(
            f"No FAISS index for '{collection}' at {path}. "
            f"Run:  python -m src.ingest"
        )
    return FAISS.load_local(
        str(path),
        llm.get_embeddings(),
        allow_dangerous_deserialization=True,  # local, self-generated index
    )


def _format(docs) -> str:
    blocks = []
    for i, d in enumerate(docs, 1):
        src = d.metadata.get("source", "?")
        sample = d.metadata.get("sample", "")
        tag = f"{src} (sample {sample})" if sample else src
        blocks.append(f"[{i}] <{tag}>\n{d.page_content.strip()}")
    return "\n\n".join(blocks) if blocks else "(no context found)"


def retrieve(collection: str, query: str, k: int | None = None) -> str:
    """Similarity search across a whole collection, returned as formatted text."""
    store = load_store(collection)
    docs = store.similarity_search(query, k=k or settings.top_k)
    return _format(docs)


def retrieve_sample(collection: str, sample: str, query: str, k: int | None = None) -> str:
    """Retrieve context restricted to one LLD sample, e.g. '3.2'."""
    store = load_store(collection)
    docs = store.similarity_search(
        query,
        k=k or settings.top_k,
        filter={"sample": sample},
    )
    return _format(docs)
