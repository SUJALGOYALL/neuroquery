from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional ,List
import pandas as pd
from sympy import python
from llm.generator import generate_sql
from utils.validator import validate_sql, is_safe
from db.executor import execute_query
from correction.intent_checker import check_intent

from typing import Dict
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
    previous_sql: List[str]

    # 🔥 NEW FIELDS
    relevant_schema: Optional[str]
    join_context: Optional[str]
    debug: List[Dict]


MAX_RETRIES = 5



def log_debug(state, node, info):
    logs = state.get("debug", []).copy()
    logs.append({
        "node": node,
        "info": info
    })
    return logs

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


# def generate_node(state: AgentState):

#     # 🔥 Generate SQL using question + feedback
#     sql = generate_sql(
#         state["question"] + "\n" + state["feedback"],
#         state["relevant_schema"],
#         state["join_context"]
#     )

#     # 🔥 Maintain history
#     previous_sql = state.get("previous_sql", []).copy()

#     if state.get("sql"):  # avoid adding None on first run
#         previous_sql.append(state["sql"])

#     return {
#         **state,
#         "sql": sql,
#         "feedback": "",          # ✅ reset feedback
#         "previous_sql": previous_sql  # ✅ store history
#     }

def generate_node(state: AgentState):

    sql = generate_sql(
        state["question"] + "\n" + state["feedback"],
        state["relevant_schema"],
        state["join_context"]
    )

    previous_sql = state.get("previous_sql", []).copy()

    if state.get("sql"):
        previous_sql.append(state["sql"])

    debug = log_debug(state, "GENERATE", {
        "question": state["question"],
        "generated_sql": sql
    })

    return {
        **state,
        "sql": sql,
        "feedback": "",
        "previous_sql": previous_sql,
        "debug": debug   # 🔥 ADD
    }




# def validate_node(state: AgentState):
#     is_valid, parsed = validate_sql(state["sql"])

#     if not is_valid:
#         return {
#             **state,
#             "feedback": f"\nFix syntax error: {parsed}",
#             "attempt": state["attempt"] + 1,
#         }

#     if not is_safe(state["sql"]):
#         return {
#             **state,
#             "feedback": "\nConvert DELETE/UPDATE into SELECT.",
#             "attempt": state["attempt"] + 1,
#         }

#     return state
def validate_node(state: AgentState):
    is_valid, parsed = validate_sql(state["sql"])

    debug = log_debug(state, "VALIDATE", {
        "sql": state["sql"],
        "is_valid": is_valid,
        "error": parsed if not is_valid else None
    })

    if not is_valid:
        return {
            **state,
            "feedback": f"\nFix syntax error: {parsed}",
            "attempt": state["attempt"] + 1,
            "debug": debug
        }

    if not is_safe(state["sql"]):
        return {
            **state,
            "feedback": "\nConvert DELETE/UPDATE into SELECT.",
            "attempt": state["attempt"] + 1,
            "debug": debug
        }

    return {**state, "debug": debug}


def intent_node(state: AgentState):
    result = check_intent(
        state["question"],
        state["sql"],
        state["relevant_schema"],
        state["join_context"]
    )
    debug = log_debug(state, "INTENT", {
        "sql": state["sql"],
        "is_correct": result.get("is_correct"),
        "issue": result.get("issue")
    })

    if not result.get("is_correct", True):

        issue = result.get("issue", "")

        previous_attempts = "\n".join(state.get("previous_sql", []))

        feedback = f"""
        Fix the SQL query.

        Issue:
        {issue}

        Reasoning Guidelines:
        - Ensure aggregation level matches grouping level
        - If grouping is done on a derived or categorical attribute,
        aggregation should come from the most granular (row-level) table
        - Avoid using pre-aggregated or summary columns when grouping by finer dimensions
        - Ensure joins follow valid relational paths

        Strict Instructions:
        - Do NOT repeat previous mistakes
        - Re-evaluate which table provides the correct level of detail
        # detect simple SQL
        simple_sql = (
            "join" not in state["sql"].lower() and
            "group by" not in state["sql"].lower()
        )

        if simple_sql:
            return state  # ✅ accept directly

        Previous attempts:
        {previous_attempts}

        Last incorrect SQL:
        {state.get("sql", "")}
        """


        return {
            **state,
            "feedback": feedback,
            "attempt": state["attempt"] + 1,
            "debug": debug
        }

    return {**state, "debug": debug}




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
