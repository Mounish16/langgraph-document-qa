"""The three document agents.

Each agent is bound to ONE document collection and answers a question strictly
from its own document:

    Agent 1 -> hld       (DOC 1  - High Level Design)
    Agent 2 -> techreq   (DOC 2  - Technical Requirements)
    Agent 3 -> lld       (DOC 3  - Low Level Design 3.1 / 3.2 / 3.3)

An agent retrieves the most relevant passages from its FAISS index and asks the
local LLM to answer using ONLY those passages. If the answer isn't in its document
it returns `found = False` (the literal token NOT_FOUND), so the evaluation agent
knows to backtrack to another agent.

No MCP, no agent-to-agent protocol — these are plain Python functions the
evaluation agent calls directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from . import llm
from .retrievers import retrieve

# Human-readable identity for each agent, keyed by collection.
AGENTS: dict[str, str] = {
    "hld": "Agent 1 - High Level Design (DOC 1)",
    "techreq": "Agent 2 - Technical Requirements (DOC 2)",
    "lld": "Agent 3 - Low Level Design (DOC 3: 3.1, 3.2, 3.3)",
}

NOT_FOUND = "NOT_FOUND"

_SYSTEM = (
    "You are {agent}. You answer questions using ONLY the excerpts from your own "
    "document shown below. Preserve identifiers verbatim (e.g. FR-2, NFR-1, AC-3, "
    "IF-2, LLD 3.2). If the answer is not contained in the excerpts, reply with "
    "exactly the single word {token} and nothing else. Do not use outside knowledge."
)


@dataclass
class AgentAnswer:
    collection: str
    agent: str
    found: bool
    answer: str
    context: str = ""
    sources: list[str] = field(default_factory=list)


def answer_from(collection: str, question: str) -> AgentAnswer:
    """Have one document agent answer `question` from its own collection."""
    if collection not in AGENTS:
        raise ValueError(f"unknown agent/collection: {collection}")

    agent = AGENTS[collection]
    context = retrieve(collection, question)

    system = _SYSTEM.format(agent=agent, token=NOT_FOUND)
    user = f"Excerpts from my document:\n\n{context}\n\nQuestion: {question}"
    reply = llm.get_llm().invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    ).content.strip()

    found = NOT_FOUND not in reply.upper()
    return AgentAnswer(
        collection=collection,
        agent=agent,
        found=found,
        answer=reply if found else "",
        context=context,
        sources=[collection],
    )
