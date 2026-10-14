from pathlib import Path

import pytest

from src import evaluation
from src.graph import build_graph, get_app


def run(question, **extra):
    return get_app().invoke({"question": question, **extra})


def test_q1_alignment_review_reads_whole_documents(indexed):
    out = run("Is LLD 3.2 related to the technical requirements and does it satisfy the HLD?")
    assert out["mode"] == "q1" and out["ident"] == "3.2"
    assert out["answer"].startswith("## Verdict")
    system, user = next(c for c in indexed.calls if "senior design reviewer" in c[0])
    # whole-document context: the LLD sample, the full TechReq and the full HLD
    assert "LOW LEVEL DESIGN 3.2" in user
    assert "TECHNICAL REQUIREMENTS" in user and "HIGH LEVEL DESIGN" in user
    assert "Data Lake" in user


def test_q2_generation_uses_all_sample_llds(indexed):
    out = run("Generate LLD 3.4 from samples 3.1/3.2/3.3")
    assert out["mode"] == "q2" and out["ident"] == "3.4"
    _, user = next(c for c in indexed.calls if "authoring a new Low Level Design" in c[0])
    for sample in ("3.1", "3.2", "3.3"):
        assert f"SAMPLE LLD {sample}" in user
    assert "Write a complete new Low Level Design LLD 3.4" in user


def test_lookup_goes_to_the_routed_agent_first(indexed):
    indexed.route_to = "techreq"
    out = run("What does FR-2 require?")
    assert out["mode"] == "lookup"
    assert out["answer"] == "Answer from techreq"
    assert out["tried"] == ["techreq"]
    assert "Agent 2" in out["answered_by"]


def test_lookup_backtracks_until_an_agent_answers(indexed):
    indexed.route_to = "hld"
    indexed.not_found = {"hld", "techreq"}
    out = run("Which storage tiers exist?")
    assert out["tried"] == ["hld", "techreq", "lld"]      # followed the routing order
    assert out["answer"] == "Answer from lld"


def test_lookup_stops_with_a_clear_message_when_nobody_knows(indexed):
    indexed.not_found = {"hld", "techreq", "lld"}
    out = run("What is the airspeed of a swallow?")
    assert out["tried"] == ["hld", "techreq", "lld"]
    assert out["answer"] == "None of the documents contain an answer to this question."


def test_answers_are_saved_and_exported(indexed):
    out = run("What are the goals in the HLD?")
    md = Path(out["output_path"])
    assert md.exists() and md.suffix == ".md"
    text = md.read_text()
    assert text.startswith("# Answer") and "What are the goals in the HLD?" in text
    assert out["files"]["md"] == md.name


def test_save_false_writes_nothing(indexed, tmp_path):
    out = run("What are the goals in the HLD?", save=False)
    assert "output_path" not in out
    assert list((tmp_path / "outputs").iterdir()) == []


def test_empty_question_is_rejected(indexed):
    with pytest.raises(ValueError):
        run("   ")


def test_answer_question_wrapper_returns_plain_dict(indexed):
    result = evaluation.answer_question("Generate LLD 3.4")
    assert result["mode"] == "q2" and result["title"] == "LLD 3.4 (generated)"
    assert Path(result["path"]).exists()


def test_graph_shape():
    nodes = set(build_graph().get_graph().nodes)
    assert {
        "collect_question", "classify_question", "review_alignment", "generate_lld",
        "route_lookup", "ask_agent", "no_answer", "export_answer",
    } <= nodes
