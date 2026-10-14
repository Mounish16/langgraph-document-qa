from src import agents


def test_agent_answers_from_its_own_document(indexed):
    result = agents.answer_from("techreq", "What does FR-2 require?")
    assert result.found and result.answer == "Answer from techreq"
    system, user = indexed.calls[-1]
    assert "ONLY the excerpts" in system
    assert "Excerpts from my document" in user
    assert "techreq.md" in user          # context really came from the techreq index


def test_agent_reports_not_found(indexed):
    indexed.not_found = {"hld"}
    result = agents.answer_from("hld", "What is the airspeed of a swallow?")
    assert not result.found and result.answer == ""


def test_unknown_collection_is_rejected(indexed):
    import pytest

    with pytest.raises(ValueError):
        agents.answer_from("nope", "hello")
