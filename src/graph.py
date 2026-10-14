"""LangGraph workflow: classify -> (review | generate | lookup loop) -> export.

The control flow lives here, as graph nodes and conditional edges:

    START -> collect_question -> classify_question
                                      |
              +-----------------------+------------------------+
              v                       v                        v
        review_alignment        generate_lld            route_lookup
            (Q1)                    (Q2)                       |
              |                       |                        v
              |                       |                  ask_agent  <--+
              |                       |                   |     |      |
              |                       |        found -----+     +--- not found,
              |                       |          |               agents left
              |                       |          |   none left
              |                       |          |       v
              |                       |          |   no_answer
              +-----------+-----------+----------+-------+
                          v
                    export_answer -> END

`classify_question` picks the branch. In the lookup branch, `route_lookup` asks the LLM
which document is most likely to hold the answer and builds an ordered list of agents;
`ask_agent` tries them one at a time. A conditional edge loops back to `ask_agent`
(backtracking) until an agent answers or every agent has said NOT_FOUND.
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import agents, evaluation
from .export import export_answer


class GraphState(TypedDict, total=False):
    question: str        # the user's question
    save: bool           # write the answer to outputs/ and export it (default True)
    mode: str            # q1 | q2 | lookup
    ident: str           # LLD id the question is about (q1/q2)
    remaining: list      # lookup: agents not yet asked, in routing order
    tried: list          # lookup: agents already asked
    answer: str          # final answer text
    title: str           # title used for the saved document
    answered_by: str     # lookup: which agent produced the answer
    files: dict          # {fmt: filename} exports (pdf/docx/md)
    output_path: str     # where the answer was saved (.md)


# --------------------------------------------------------------------------- #
# Nodes                                                                       #
# --------------------------------------------------------------------------- #

def collect_question(state: GraphState) -> GraphState:
    question = (state.get("question") or "").strip()
    if not question:
        raise ValueError("no question provided")
    print(f"[graph] question: {question[:80]}")
    return {"question": question, "save": state.get("save", True), "tried": []}


def classify_question(state: GraphState) -> GraphState:
    mode, ident = evaluation.classify(state["question"])
    print(f"[graph] mode: {mode}" + (f" (LLD {ident})" if ident else ""))
    return {"mode": mode, "ident": ident or ""}


def review_alignment(state: GraphState) -> GraphState:
    answer, title = evaluation.answer_q1(state["ident"])
    return {"answer": answer, "title": title}


def generate_lld(state: GraphState) -> GraphState:
    answer, title = evaluation.answer_q2(state["ident"])
    return {"answer": answer, "title": title}


def route_lookup(state: GraphState) -> GraphState:
    order = evaluation.routing_order(state["question"])
    print(f"[graph] routing order: {' > '.join(order)}")
    return {"remaining": order, "tried": []}


def ask_agent(state: GraphState) -> GraphState:
    remaining = list(state["remaining"])
    collection = remaining.pop(0)
    result = agents.answer_from(collection, state["question"])
    print(f"[graph] {collection}: {'found' if result.found else 'NOT_FOUND'}")
    update: GraphState = {
        "remaining": remaining,
        "tried": list(state.get("tried", [])) + [collection],
    }
    if result.found:
        update.update(answer=result.answer, title="Answer", answered_by=result.agent)
    return update


def no_answer(state: GraphState) -> GraphState:
    return {
        "answer": "None of the documents contain an answer to this question.",
        "title": "Answer",
    }


def export(state: GraphState) -> GraphState:
    if not state.get("save", True):
        return {}
    md = evaluation.save_md(state["title"], state["question"], state["answer"])
    files = export_answer(md)
    return {"output_path": str(md), "files": {fmt: Path(p).name for fmt, p in files.items()}}


# --------------------------------------------------------------------------- #
# Conditional edges                                                           #
# --------------------------------------------------------------------------- #

def pick_branch(state: GraphState) -> str:
    return {"q1": "review_alignment", "q2": "generate_lld"}.get(state["mode"], "route_lookup")


def after_agent(state: GraphState) -> str:
    if state.get("answered_by"):
        return "export_answer"
    return "ask_agent" if state.get("remaining") else "no_answer"


# --------------------------------------------------------------------------- #
# Assembly                                                                    #
# --------------------------------------------------------------------------- #

def build_graph():
    g = StateGraph(GraphState)
    g.add_node("collect_question", collect_question)
    g.add_node("classify_question", classify_question)
    g.add_node("review_alignment", review_alignment)
    g.add_node("generate_lld", generate_lld)
    g.add_node("route_lookup", route_lookup)
    g.add_node("ask_agent", ask_agent)
    g.add_node("no_answer", no_answer)
    g.add_node("export_answer", export)

    g.add_edge(START, "collect_question")
    g.add_edge("collect_question", "classify_question")
    g.add_conditional_edges(
        "classify_question",
        pick_branch,
        ["review_alignment", "generate_lld", "route_lookup"],
    )
    g.add_edge("route_lookup", "ask_agent")
    g.add_conditional_edges("ask_agent", after_agent, ["ask_agent", "no_answer", "export_answer"])
    g.add_edge("review_alignment", "export_answer")
    g.add_edge("generate_lld", "export_answer")
    g.add_edge("no_answer", "export_answer")
    g.add_edge("export_answer", END)
    return g.compile()


_APP = None


def get_app():
    """Compile the graph once and reuse it."""
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP
