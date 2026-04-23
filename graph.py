"""
graph.py — LangGraph workflow for the RAG Customer Support Assistant.
"""

from typing import TypedDict
import chromadb
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langgraph.graph import StateGraph, END
from prompts import RAG_PROMPT, ESCALATION_MESSAGE

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LLM_MODEL = "llama3.1:8b"
EMBEDDING_MODEL = "nomic-embed-text"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "support_kb"
TOP_K = 3
MIN_DOCS_THRESHOLD = 1
MIN_QUERY_LENGTH = 3


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class SupportState(TypedDict):
    query: str
    retrieved_docs: list[str]
    answer: str
    needs_escalation: bool        # renamed from 'escalate'
    escalation_reason: str
    final_response: str


# ---------------------------------------------------------------------------
# Node 1 — Router
# ---------------------------------------------------------------------------

def router_node(state: SupportState) -> SupportState:
    query = state["query"].strip()

    if len(query) < MIN_QUERY_LENGTH:
        return {
            **state,
            "needs_escalation": True,
            "escalation_reason": "Query is too short or unclear.",
        }

    word_count = len([w for w in query.split() if w.isalpha()])
    if word_count == 0:
        return {
            **state,
            "needs_escalation": True,
            "escalation_reason": "Query contains no recognisable words.",
        }

    return {**state, "needs_escalation": False, "escalation_reason": ""}


# ---------------------------------------------------------------------------
# Node 2 — Process
# ---------------------------------------------------------------------------

def process_node(state: SupportState) -> SupportState:
    query = state["query"]

    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        return {
            **state,
            "needs_escalation": True,
            "escalation_reason": f"Knowledge base not found. Run ingest.py first. ({e})",
            "retrieved_docs": [],
            "answer": "",
        }

    embedder = OllamaEmbeddings(model=EMBEDDING_MODEL)
    query_embedding = embedder.embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
    )

    docs: list[str] = results.get("documents", [[]])[0]

    if len(docs) < MIN_DOCS_THRESHOLD:
        return {
            **state,
            "needs_escalation": True,
            "escalation_reason": "Not enough relevant information found.",
            "retrieved_docs": docs,
            "answer": "",
        }

    context = "\n\n---\n\n".join(docs)
    prompt = RAG_PROMPT.format(context=context, question=query)

    try:
        llm = OllamaLLM(model=LLM_MODEL)
        answer = llm.invoke(prompt).strip()
    except Exception as e:
        return {
            **state,
            "needs_escalation": True,
            "escalation_reason": f"LLM failed. ({e})",
            "retrieved_docs": docs,
            "answer": "",
        }

    if "i don't know" in answer.lower():
        return {
            **state,
            "needs_escalation": True,
            "escalation_reason": "Answer not found in knowledge base.",
            "retrieved_docs": docs,
            "answer": answer,
        }

    return {
        **state,
        "needs_escalation": False,
        "retrieved_docs": docs,
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# Node 3 — Output
# ---------------------------------------------------------------------------

def output_node(state: SupportState) -> SupportState:
    return {**state, "final_response": state["answer"]}


# ---------------------------------------------------------------------------
# Node 4 — Escalate (HITL)
# ---------------------------------------------------------------------------

def escalate_node(state: SupportState) -> SupportState:
    reason = state.get("escalation_reason", "Unknown reason.")
    message = ESCALATION_MESSAGE.format(reason=reason)
    return {**state, "final_response": message}


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------

def check_escalation(state: SupportState) -> str:
    if state.get("needs_escalation", False):
        return "escalate"
    return "continue"


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(SupportState)

    graph.add_node("router", router_node)
    graph.add_node("process", process_node)
    graph.add_node("output", output_node)
    graph.add_node("escalate", escalate_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        check_escalation,
        {"escalate": "escalate", "continue": "process"},
    )

    graph.add_conditional_edges(
        "process",
        check_escalation,
        {"escalate": "escalate", "continue": "output"},
    )

    graph.add_edge("output", END)
    graph.add_edge("escalate", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def run_query(query: str) -> dict:
    app = build_graph()

    initial_state: SupportState = {
        "query": query,
        "retrieved_docs": [],
        "answer": "",
        "needs_escalation": False,
        "escalation_reason": "",
        "final_response": "",
    }

    return app.invoke(initial_state)