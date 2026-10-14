import shutil

import pytest

from src import export


def test_markdown_is_the_fallback_when_pandoc_is_missing(tmp_path, monkeypatch):
    md = tmp_path / "a.md"
    md.write_text("# Title\n\nbody\n")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert export.export_answer(md) == {"md": str(md)}


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_docx_is_produced_when_pandoc_is_available(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Title\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    out = export.export_answer(md)
    assert out["md"] == str(md)
    assert (tmp_path / "a.docx").exists() and "docx" in out
