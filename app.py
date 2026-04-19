import streamlit as st
import pandas as pd

from db.connection import get_connection
from utils.schema import get_schema
from utils.metrics import MetricsTracker

# 🔥 LangGraph Agent
from agent.sql_agent import build_graph


# ================= INIT METRICS =================
if "metrics" not in st.session_state:
    st.session_state.metrics = MetricsTracker()

metrics = st.session_state.metrics


# ================= UI =================
st.set_page_config(page_title="NeuroQuery", layout="wide")
st.title("🧠 NeuroQuery - NLP to SQL (LangGraph Powered)")

question = st.text_input("💬 Ask your query:")


if question:

    metrics.log_query()
    start_time = metrics.start_timer()

    conn = get_connection()
    cursor = conn.cursor()

    st.write("🔍 Fetching schema...")
    full_schema = get_schema(cursor)

    # ================= GRAPH =================
    graph = build_graph()

    state = {
        "question": question,
        "schema": full_schema,
        "sql": None,
        "feedback": "",
        "df": None,
        "error": None,
        "attempt": 0,
        "cursor": cursor,
        "relevant_schema": None,
        "join_context": None
    }

    st.write("🤖 Running AI Agent...")

    with st.spinner("Thinking..."):
        result = graph.invoke(state)

    # ================= METRICS =================
    if result.get("df") is not None:
        metrics.log_success()
    else:
        metrics.log_failure()

    metrics.end_timer(start_time)

    # ================= OUTPUT =================

    tab1, tab2, tab3 = st.tabs(["📊 Result", "🧠 SQL", "🐞 Debug"])

    # ===== RESULT =====
    with tab1:
        st.subheader("📊 Query Result")

        if result.get("df") is not None:
            st.dataframe(result["df"], use_container_width=True)
        else:
            st.error("❌ Failed to generate correct SQL")

    # ===== SQL =====
    with tab2:
        st.subheader("🧠 Final SQL")
        st.code(result.get("sql", "No SQL generated"), language="sql")

    # ===== DEBUG =====
    with tab3:
        st.subheader("🐞 Debug Info")

        st.write("Attempts:", result.get("attempt"))
        st.write("Final Feedback:", result.get("feedback"))

        with st.expander("📦 Full Schema"):
            st.text(full_schema)

        with st.expander("🎯 RAG Schema"):
            st.text(result.get("relevant_schema"))

        with st.expander("🔗 Join Context"):
            st.text(result.get("join_context"))

    # ================= SIDEBAR =================
    st.sidebar.title("🧾 Debug Logs")
    st.sidebar.write("Query:", question)
    st.sidebar.code(result.get("sql", ""), language="sql")

    st.sidebar.markdown("### 📊 System Metrics")

    report = metrics.report()

    for key, value in report.items():
        st.sidebar.write(f"{key}: {value}")

    cursor.close()
    conn.close()
