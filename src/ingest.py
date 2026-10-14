"""Build one FAISS index per document collection.

Layout expected under data/:
    data/doc1_hld/*        -> collection "hld"      (DOC 1, HLD)
    data/doc2_techreq/*    -> collection "techreq"  (DOC 2, Technical Requirements)
    data/doc3_lld/*        -> collection "lld"      (DOC 3: 3.1, 3.2, 3.3 ...)

Supported file types: .pdf, .md, .txt

Each LLD sample (3.1, 3.2, ...) is tagged with a `sample` metadata field derived
from its filename (e.g. "lld_3.2.md" -> sample "3.2"), so the evaluation agent can
retrieve a single sample on demand.
"""
from __future__ import annotations

import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import llm
from .config import COLLECTIONS, settings

_SAMPLE_RE = re.compile(r"(\d+\.\d+)")


def _load_file(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    if suffix in {".md", ".txt"}:
        return TextLoader(str(path), encoding="utf-8").load()
    return []


def _load_collection(folder: Path, collection: str) -> list[Document]:
    docs: list[Document] = []
    if not folder.exists():
        return docs
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        loaded = _load_file(path)
        if not loaded:
            continue
        sample_match = _SAMPLE_RE.search(path.stem)
        sample = sample_match.group(1) if sample_match else ""
        for d in loaded:
            d.metadata.update(
                collection=collection,
                source=path.name,
                sample=sample,
            )
        docs.extend(loaded)
    return docs


def build_index(collection: str) -> int:
    """Build and persist the FAISS index for one collection. Returns chunk count."""
    folder = settings.data_dir / COLLECTIONS[collection]
    raw = _load_collection(folder, collection)
    if not raw:
        print(f"[ingest] WARNING: no files found in {folder} for '{collection}'")
        return 0

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(raw)

    store = FAISS.from_documents(chunks, llm.get_embeddings())
    out = settings.index_dir / collection
    store.save_local(str(out))
    print(f"[ingest] '{collection}': {len(raw)} docs -> {len(chunks)} chunks -> {out}")
    return len(chunks)


def build_all() -> None:
    total = 0
    for collection in COLLECTIONS:
        total += build_index(collection)
    print(f"[ingest] done. {total} chunks across {len(COLLECTIONS)} collections.")


if __name__ == "__main__":
    build_all()
