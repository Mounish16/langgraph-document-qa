"""Agent 4 - the evaluation agent: the logic behind each question type.

It answers three kinds of question, all grounded ONLY in the local documents:

  Q1  alignment  - "Is LLD 3.2 related to the Technical Requirements and does it
                    satisfy the HLD?"  -> pulls LLD 3.2 + full TechReq + full HLD and
                    produces a verdict, a requirement-by-requirement traceability
                    table, gaps and a recommendation.

  Q2  generation - "Generate LLD 3.4 from samples 3.1/3.2/3.3 so it satisfies both the
                    Technical Requirements and the HLD."  -> pulls all sample LLDs +
                    full TechReq + full HLD and writes a complete new LLD.

  lookup         - any other question -> routed to the single most relevant document
                    agent, with backtracking to the others on NOT_FOUND.

This module holds the pure steps (classify, answer_q1, answer_q2, route, save).
The control flow between them - the conditional routing and the backtracking loop -
lives in `graph.py` as LangGraph nodes and edges.

The documents are small, so Q1/Q2 feed the whole TechReq and HLD to the model for
faithful, detailed answers instead of chunk snippets.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from . import llm
from .config import COLLECTIONS, settings
from .ingest import _load_collection

EXISTING_LLD_SAMPLES = ("3.1", "3.2", "3.3")


# --------------------------------------------------------------------------- #
# Document loading                                                            #
# --------------------------------------------------------------------------- #

def full_text(collection: str) -> str:
    folder = settings.data_dir / COLLECTIONS[collection]
    docs = _load_collection(folder, collection)
    return "\n\n".join(d.page_content for d in docs)


def sample_text(sample: str) -> str:
    folder = settings.data_dir / COLLECTIONS["lld"]
    docs = _load_collection(folder, "lld")
    parts = [d.page_content for d in docs if d.metadata.get("sample") == sample]
    return "\n\n".join(parts)


def _chat(system: str, user: str) -> str:
    return llm.get_llm().invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    ).content.strip()


# --------------------------------------------------------------------------- #
# Classification                                                              #
# --------------------------------------------------------------------------- #

# Word-boundary patterns. Matching whole words (not substrings) keeps ordinary
# questions such as "Does the HLD make use of Kafka?" or "Which component builds the
# pipeline?" from being mistaken for a generation request.
_GENERATE_RE = re.compile(
    r"\b(generate|generates|create|produce|draft|write|author|make|build)\b", re.IGNORECASE
)
_EVALUATE_RE = re.compile(
    r"\b(satisf\w*|relat\w*|align\w*|evaluat\w*|complian\w*|compl(?:y|ies)|consisten\w*"
    r"|verif\w*|assess\w*|review\w*|trace\w*)",
    re.IGNORECASE,
)
# The request must actually be about an LLD for Q1/Q2 to apply.
_LLD_RE = re.compile(r"\blld\b|low[- ]level design", re.IGNORECASE)
_ID_RE = re.compile(r"\b\d+\.\d+\b")


def classify(question: str) -> tuple[str, str | None]:
    """Return (mode, ident): mode is 'q1' | 'q2' | 'lookup'.

    Q1/Q2 only apply to questions about an LLD. In generation mode the target id is the
    number that is NOT one of the existing samples (3.1/3.2/3.3); if none is given it
    defaults to 3.4. Everything else is a lookup.
    """
    if not _LLD_RE.search(question):
        return "lookup", None

    ids = _ID_RE.findall(question)
    new = next((i for i in ids if i not in EXISTING_LLD_SAMPLES), None)

    if _GENERATE_RE.search(question):
        return "q2", new or "3.4"
    if ids and _EVALUATE_RE.search(question):
        return "q1", ids[0]
    if new:
        return "q2", new
    return "lookup", None


# --------------------------------------------------------------------------- #
# Q1 - alignment review                                                       #
# --------------------------------------------------------------------------- #

_Q1_SYSTEM = (
    "You are a senior design reviewer. You assess whether a Low Level Design sample is "
    "related to the Technical Requirements and whether it satisfies the High Level "
    "Design. Use ONLY the documents provided. Preserve every identifier verbatim "
    "(FR-*, NFR-*, AC-*, IF-*, and HLD component names). Be thorough and specific."
)


def answer_q1(sample: str) -> tuple[str, str]:
    lld = sample_text(sample)
    if not lld.strip():
        return (
            f"LLD {sample} was not found under data/{COLLECTIONS['lld']}.", f"Q1 - LLD {sample}"
        )
    user = (
        f"LOW LEVEL DESIGN {sample}:\n{lld}\n\n"
        f"TECHNICAL REQUIREMENTS (DOC 2):\n{full_text('techreq')}\n\n"
        f"HIGH LEVEL DESIGN (DOC 1):\n{full_text('hld')}\n\n"
        f"Question: Is LLD {sample} related to the Technical Requirements, and does it "
        f"satisfy the HLD?\n\n"
        "Answer in Markdown with exactly these sections:\n"
        "## Verdict\nAligned / Partially aligned / Not aligned, plus a one-sentence reason.\n"
        "## Traceability\nA Markdown table with columns: Requirement or HLD element | "
        f"Where LLD {sample} addresses it | Status (met / partial / missing). Include every "
        "relevant FR, NFR, AC and HLD component.\n"
        "## Gaps and contradictions\n"
        "## Recommendation"
    )
    return _chat(_Q1_SYSTEM, user), f"Q1 - LLD {sample} alignment review"


# --------------------------------------------------------------------------- #
# Q2 - generate a new LLD                                                     #
# --------------------------------------------------------------------------- #

_Q2_SYSTEM = (
    "You are a senior designer authoring a new Low Level Design. Follow the section "
    "structure of the sample LLDs and satisfy every Technical Requirement and HLD "
    "constraint. Ground everything in the documents provided. Preserve every identifier "
    "verbatim (FR-*, NFR-*, AC-*, IF-*, and HLD component names)."
)


def answer_q2(new_id: str) -> tuple[str, str]:
    samples = "\n\n".join(
        f"--- SAMPLE LLD {s} ---\n{sample_text(s)}" for s in EXISTING_LLD_SAMPLES
    )
    user = (
        f"SAMPLE LOW LEVEL DESIGNS (mirror this structure):\n{samples}\n\n"
        f"TECHNICAL REQUIREMENTS (DOC 2):\n{full_text('techreq')}\n\n"
        f"HIGH LEVEL DESIGN (DOC 1):\n{full_text('hld')}\n\n"
        f"Task: Write a complete new Low Level Design LLD {new_id}, modeled on the sample "
        "LLDs, that satisfies both the Technical Requirements and the HLD.\n\n"
        f"Output a full Markdown LLD document titled 'DOC 3.{new_id.split('.')[-1]} - Low "
        f"Level Design'. Use the same section structure as the samples (Scope, Module "
        "structure, Interfaces, Data model, Sequences, etc.). End with:\n"
        "## Requirements coverage\nA table mapping each relevant FR/NFR/AC to the section "
        "that satisfies it.\n"
        "## Assumptions"
    )
    return _chat(_Q2_SYSTEM, user), f"LLD {new_id} (generated)"


# --------------------------------------------------------------------------- #
# Lookup - route to one agent, backtrack to the others                        #
# --------------------------------------------------------------------------- #

ROUTE_ORDER = ["hld", "techreq", "lld"]

_ROUTER_SYSTEM = (
    "You route a question to the single document most likely to answer it. Reply with "
    "exactly one word:\n"
    "  hld     - high level design: goals, architecture, major components, constraints\n"
    "  techreq - technical requirements: FR/NFR/IF/AC items, acceptance criteria\n"
    "  lld     - low level design: detailed modules/interfaces of samples 3.1, 3.2, 3.3\n"
    "Reply with only one of: hld, techreq, lld."
)

_HINTS = {
    "techreq": ("requirement", "fr-", "nfr-", "if-", "ac-", "acceptance"),
    "lld": ("lld", "low level", "3.1", "3.2", "3.3", "module", "interface", "sequence"),
    "hld": ("hld", "high level", "architecture", "component", "goal", "constraint"),
}


def route(question: str) -> str:
    """Pick the document most likely to hold the answer (LLM first, keyword fallback)."""
    reply = _chat(_ROUTER_SYSTEM, question).lower()
    for c in ROUTE_ORDER:
        if c in reply:
            return c
    q = question.lower()
    scores = {c: sum(k in q for k in kws) for c, kws in _HINTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "hld"


def routing_order(question: str) -> list[str]:
    """Primary document first, then the rest in a fixed order (the backtracking path)."""
    primary = route(question)
    return [primary] + [c for c in ROUTE_ORDER if c != primary]


# --------------------------------------------------------------------------- #
# Saving                                                                      #
# --------------------------------------------------------------------------- #

def save_md(title: str, question: str, answer: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:40].strip("_")
    path = settings.output_dir / f"{stamp}_{slug or 'answer'}.md"
    path.write_text(f"# {title}\n\n*{question}*\n\n{answer}\n", encoding="utf-8")
    return path


def answer_question(question: str, save: bool = True) -> dict:
    """Run the LangGraph workflow for one question and return a plain result dict."""
    from .graph import get_app  # imported lazily: graph.py imports this module

    question = (question or "").strip()
    if not question:
        raise ValueError("question is empty")

    state = get_app().invoke({"question": question, "save": save})
    result = {
        "question": question,
        "mode": state["mode"],
        "ident": state.get("ident"),
        "answer": state["answer"],
        "title": state["title"],
    }
    if state.get("output_path"):
        result["path"] = state["output_path"]
        result["files"] = state.get("files", {})
    return result
