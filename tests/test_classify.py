import pytest

from src.evaluation import classify


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Is LLD 3.2 related to the technical requirements and does it satisfy the HLD?", ("q1", "3.2")),
        ("Does LLD 3.1 comply with the Technical Requirements?", ("q1", "3.1")),
        ("Review LLD 3.3 against the HLD", ("q1", "3.3")),
        ("Generate LLD 3.4 from 3.1/3.2/3.3 satisfying the technical requirements and HLD", ("q2", "3.4")),
        ("Please draft LLD 3.7", ("q2", "3.7")),
        ("Write a new low level design for the alerting service", ("q2", "3.4")),
        ("LLD 3.5", ("q2", "3.5")),
    ],
)
def test_lld_questions(question, expected):
    assert classify(question) == expected


@pytest.mark.parametrize(
    "question",
    [
        "What are the goals in the HLD?",
        "Summarise LLD 3.2",
        "What does NFR-3 say about how data is written to the lake?",
        # Regression: these used to be misread as "generate LLD 3.4" (substring match).
        "Does the HLD make use of Kafka?",
        "Which component builds the ingestion pipeline?",
        "Who will write the ingest connectors in the HLD?",
        "Which requirements relate to security?",
    ],
)
def test_everything_else_is_a_lookup(question):
    assert classify(question) == ("lookup", None)


def test_existing_sample_id_is_never_the_generation_target():
    assert classify("Generate LLD 3.2 again")[1] == "3.4"
