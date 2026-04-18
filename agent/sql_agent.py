from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import pandas as pd

from llm.generator import generate_sql
from utils.validator import validate_sql, is_safe
from db.executor import execute_query
from correction.intent_checker import check_intent


# ---------------- STATE ----------------
class AgentState(TypedDict):
    question: str
    schema: str
    sql: Optional[str]
    feedback: str
    df: Optional[pd.DataFrame]
    error: Optional[str]
    attempt: int


MAX_RETRIES = 2


# ---------------- NODES ----------------

def generate_node(state: AgentState):
    sql = generate_sql(state["question"] + state["feedback"], state["schema"])
    return {**state, "sql": sql}


def validate_node(state: AgentState):
    is_valid, parsed = validate_sql(state["sql"])

    if not is_valid:
        return {
            **state,
            "feedback": f"\nFix syntax error: {parsed}",
            "attempt": state["attempt"] + 1,
        }

    if not is_safe(state["sql"]):
        return {**state, "error": "Unsafe query"}

    return state


def execute_node(state: AgentState):
    try:
        rows, cols = execute_query(state["cursor"], state["sql"])
        df = pd.DataFrame(rows, columns=cols)

        return {**state, "df": df}

    except Exception as e:
        return {
            **state,
            "feedback": f"\nFix execution error: {str(e)}",
            "attempt": state["attempt"] + 1,
        }


def intent_node(state: AgentState):
    if state["df"] is not None and not state["df"].empty:
        result = check_intent(state["question"], state["sql"])

        if not result.get("is_correct", True):
            return {
                **state,
                "feedback": f"\nFix this issue: {result.get('issue')}",
                "attempt": state["attempt"] + 1,
            }

    return state


# ---------------- ROUTER ----------------

def should_retry(state: AgentState):
    if state.get("error"):
        return END

    if state["attempt"] >= MAX_RETRIES:
        return END

    if state.get("df") is None or state["df"].empty:
        return "generate"

    return END


# ---------------- BUILD GRAPH ----------------

def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("generate", generate_node)
    builder.add_node("validate", validate_node)
    builder.add_node("execute", execute_node)
    builder.add_node("intent", intent_node)

    builder.set_entry_point("generate")

    builder.add_edge("generate", "validate")
    builder.add_edge("validate", "execute")
    builder.add_edge("execute", "intent")

    builder.add_conditional_edges(
        "intent",
        should_retry,
        {
            "generate": "generate",
            END: END
        }
    )

    return builder.compile()