"""Central configuration, loaded from environment (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root = one level up from this file's parent (src/)
ROOT = Path(__file__).resolve().parent.parent


def _path(env_key: str, default: str) -> Path:
    p = Path(os.getenv(env_key, default))
    return p if p.is_absolute() else ROOT / p


@dataclass
class Settings:
    # --- LLM (local, served by Ollama in Docker) ---
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "llama3.1")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    # Q1/Q2 feed whole documents to the model, so keep a large context window.
    # ~8k tokens of docs + prompt + generation; 16384 leaves comfortable headroom.
    num_ctx: int = int(os.getenv("LLM_NUM_CTX", "16384"))

    # --- Retrieval ---
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    top_k: int = int(os.getenv("TOP_K", "5"))

    # --- Paths ---
    data_dir: Path = field(default_factory=lambda: _path("DATA_DIR", "data"))
    index_dir: Path = field(default_factory=lambda: _path("INDEX_DIR", "faiss_index"))
    output_dir: Path = field(default_factory=lambda: _path("OUTPUT_DIR", "outputs"))

    def __post_init__(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Logical document collections. Each maps a collection name -> subfolder under data/.
# Agent 1 -> HLD, Agent 2 -> Technical Requirements, Agent 3 -> LLD samples.
COLLECTIONS: dict[str, str] = {
    "hld": "doc1_hld",              # DOC 1  - High Level Design
    "techreq": "doc2_techreq",      # DOC 2  - Technical Requirements
    "lld": "doc3_lld",              # DOC 3  - Low Level Design (3.1, 3.2, 3.3)
}

settings = Settings()
