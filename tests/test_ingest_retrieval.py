from src import ingest, retrievers
from src.config import COLLECTIONS, settings


def test_build_all_creates_one_index_per_collection(sandbox):
    ingest.build_all()
    for collection in COLLECTIONS:
        assert (settings.index_dir / collection / "index.faiss").exists()


def test_lld_samples_are_tagged_from_their_filenames():
    folder = settings.data_dir / COLLECTIONS["lld"]
    docs = ingest._load_collection(folder, "lld")
    assert {d.metadata["sample"] for d in docs} == {"3.1", "3.2", "3.3"}
    assert all(d.metadata["collection"] == "lld" for d in docs)


def test_retrieve_returns_numbered_sourced_context(indexed):
    text = retrievers.retrieve("techreq", "acceptance criteria", k=2)
    assert text.startswith("[1] <techreq.md>")
    assert "[2]" in text


def test_retrieve_sample_filters_to_one_lld(indexed):
    text = retrievers.retrieve_sample("lld", "3.2", "data lake storage", k=3)
    assert "sample 3.2" in text
    assert "sample 3.1" not in text and "sample 3.3" not in text


def test_missing_index_gives_a_helpful_error(sandbox):
    import pytest

    with pytest.raises(FileNotFoundError, match="python -m src.ingest"):
        retrievers.load_store("hld")
