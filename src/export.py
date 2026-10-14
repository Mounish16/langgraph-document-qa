"""Export a Markdown answer to .docx and .pdf.

Uses `pandoc` for the conversion (already installed in the Docker image). PDF is
produced with a HTML-based engine (wkhtmltopdf) so no LaTeX toolchain is needed.
Everything is best-effort: if a converter is missing the function simply omits that
format. Markdown is always returned as the fallback.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str], timeout: int) -> None:
    subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)


def export_answer(md_path: str | Path) -> dict[str, str]:
    """Produce .docx and .pdf next to `md_path`. Returns {fmt: path} for successes."""
    md_path = Path(md_path)
    out: dict[str, str] = {"md": str(md_path)}

    if not shutil.which("pandoc"):
        return out

    # DOCX — pandoc handles this natively, no extra engine required.
    docx = md_path.with_suffix(".docx")
    try:
        _run(["pandoc", str(md_path), "-o", str(docx)], 120)
        out["docx"] = str(docx)
    except Exception as e:  # noqa: BLE001
        print(f"[export] docx failed: {e}")

    # PDF — try HTML-based engines first (no LaTeX), then LaTeX as a last resort.
    pdf = md_path.with_suffix(".pdf")
    for engine in ("weasyprint", "wkhtmltopdf", "pdflatex"):
        if not shutil.which(engine):
            continue
        try:
            _run(["pandoc", str(md_path), "-o", str(pdf), f"--pdf-engine={engine}"], 240)
            out["pdf"] = str(pdf)
            break
        except Exception as e:  # noqa: BLE001
            print(f"[export] pdf via {engine} failed: {e}")

    return out
