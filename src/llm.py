"""LLM + embedding clients pointing at the local Ollama server (Docker Hub image).

Everything is served locally: no data leaves the machine. The chat model is
OpenAI-compatible, so swapping to vLLM/LocalAI later only means changing the
base URL and model name in .env.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_ollama import ChatOllama, OllamaEmbeddings

from .config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    """Chat model used by every agent."""
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.llm_model,
        temperature=settings.temperature,
        num_ctx=settings.num_ctx,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> OllamaEmbeddings:
    """Embedding model used to build/query FAISS."""
    return OllamaEmbeddings(
        base_url=settings.ollama_base_url,
        model=settings.embed_model,
    )
