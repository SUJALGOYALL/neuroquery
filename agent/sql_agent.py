from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import pandas as pd

from llm.generator import generate_sql
from utils.validator import validate_sql, is_safe
from db.executor import execute_query
from correction.intent_checker import check_intent

# 🔥 NEW IMPORTS
from rag.rag_pipeline import RAGPipeline
from utils.join_graph import build_join_graph
from utils.join_path_finder import (
    find_multi_join_path,
    format_join_path,
    extract_tables_from_schema
)
from utils.schema import get_foreign_keys


# ---------------- STATE ----------------
class AgentState(TypedDict):
    question: str
    schema: str
    sql: Optional[str]
    feedback: str
    df: Optional[pd.DataFrame]
    error: Optional[str]
    attempt: int
    cursor: object

    # 🔥 NEW FIELDS
    relevant_schema: Optional[str]
    join_context: Optional[str]


MAX_RETRIES = 2


# ---------------- NODES ----------------

def rag_node(state: AgentState):
    rag = RAGPipeline(state["schema"])
    relevant_schema = rag.retrieve(state["question"])

    return {**state, "relevant_schema": relevant_schema}


def join_node(state: AgentState):
    relationships = get_foreign_keys(state["cursor"])
    join_graph = build_join_graph(relationships)

    tables = extract_tables_from_schema(state["relevant_schema"])
    tables = tables[:3]  # reduce noise

    join_path = find_multi_join_path(join_graph, tables)
    join_context = format_join_path(join_path)

    return {**state, "join_context": join_context}


def generate_node(state: AgentState):
    sql = generate_sql(
        state["question"] + state["feedback"],
        state["relevant_schema"],
        state["join_context"]
    )

    return {**state, "sql": sql, "feedback": ""}


def validate_node(state: AgentState):
    is_valid, parsed = validate_sql(state["sql"])

    if not is_valid:
        return {
            **state,
            "feedback": f"\nFix syntax error: {parsed}",
            "attempt": state["attempt"] + 1,
        }

    if not is_safe(state["sql"]):
        return {
            **state,
            "feedback": "\nConvert DELETE/UPDATE into SELECT.",
            "attempt": state["attempt"] + 1,
        }

    return state


def intent_node(state: AgentState):
    result = check_intent(
        state["question"],
        state["sql"],
        state["relevant_schema"],
        state["join_context"]
    )

    if not result.get("is_correct", True):
        return {
            **state,
            "feedback": f"\nFix this issue: {result.get('issue')}",
            "attempt": state["attempt"] + 1,
        }

    return state


def execute_node(state: AgentState):
    try:
        rows, cols = execute_query(state["cursor"], state["sql"])
        df = pd.DataFrame(rows, columns=cols)

        if df.empty:
            return {
                **state,
                "feedback": "\nQuery returned no results.",
                "attempt": state["attempt"] + 1,
            }

        return {**state, "df": df}

    except Exception as e:
        return {
            **state,
            "feedback": f"\nFix execution error: {str(e)}",
            "attempt": state["attempt"] + 1,
        }


# ---------------- ROUTERS ----------------

def route_validate(state: AgentState):
    if state["attempt"] >= MAX_RETRIES:
        return END
    if state.get("feedback"):
        return "generate"
    return "intent"


def route_intent(state: AgentState):
    if state["attempt"] >= MAX_RETRIES:
        return END
    if state.get("feedback"):
        return "generate"
    return "execute"


def route_execute(state: AgentState):
    if state["attempt"] >= MAX_RETRIES:
        return END
    if state.get("feedback"):
        return "generate"
    return END


# ---------------- BUILD GRAPH ----------------

def build_graph():
    builder = StateGraph(AgentState)

    # 🔥 NODES
    builder.add_node("rag", rag_node)
    builder.add_node("join", join_node)
    builder.add_node("generate", generate_node)
    builder.add_node("validate", validate_node)
    builder.add_node("intent", intent_node)
    builder.add_node("execute", execute_node)

    # 🔥 ENTRY
    builder.set_entry_point("rag")

    # 🔥 FLOW
    builder.add_edge("rag", "join")
    builder.add_edge("join", "generate")
    builder.add_edge("generate", "validate")

    builder.add_conditional_edges(
        "validate",
        route_validate,
        {
            "generate": "generate",
            "intent": "intent",
            END: END
        }
    )

    builder.add_conditional_edges(
        "intent",
        route_intent,
        {
            "generate": "generate",
            "execute": "execute",
            END: END
        }
    )

    builder.add_conditional_edges(
        "execute",
        route_execute,
        {
            "generate": "generate",
            END: END
        }
    )

    return builder.compile()
