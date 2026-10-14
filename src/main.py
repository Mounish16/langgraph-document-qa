"""CLI entrypoint.

Examples:
    python -m src.ingest                          # build FAISS indexes from data/
    python -m src.main "Is LLD 3.2 related to the technical requirements and does it satisfy the HLD?"
    python -m src.main "Generate LLD 3.4 from 3.1/3.2/3.3 satisfying the technical requirements and HLD"
    python -m src.main "What are the goals in the HLD?"
"""
from __future__ import annotations

import argparse

from .graph import get_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the HLD/TechReq/LLD evaluation agent")
    parser.add_argument("question", help="the question to ask")
    args = parser.parse_args()

    result = get_app().invoke({"question": args.question})

    print("\n" + "=" * 70)
    print(result.get("answer", "(no answer)"))
    print("=" * 70)
    files = result.get("files", {})
    if files:
        print("Saved:", ", ".join(f"{fmt} -> outputs/{name}" for fmt, name in files.items()))


if __name__ == "__main__":
    main()
