import streamlit as st
import pandas as pd
from db.connection import get_connection
from db.executor import execute_query
from llm.generator import generate_sql
from utils.schema import get_schema
from rag.rag_pipeline import RAGPipeline

# 🔥 Validator
from utils.validator import is_safe, validate_sql, extract_tables, extract_columns

# 🔥 NEW: Intent Checker
from correction.intent_checker import check_intent


# ================= CLEAN SQL =================
def clean_sql(sql):
    sql = sql.strip()

    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()

    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    return sql


# ================= UI =================
st.set_page_config(page_title="NeuroQuery", layout="wide")
st.title("🧠 NeuroQuery - NLP to SQL (Self-Correcting)")

question = st.text_input("💬 Ask your query:")


if question:

    steps = {}
    progress = st.progress(0)

    conn = get_connection()
    cursor = conn.cursor()

    # ================= SCHEMA =================
    st.write("🔍 Fetching schema...")
    full_schema = get_schema(cursor)
    steps["full_schema"] = full_schema
    progress.progress(20)

    # ================= RAG =================
    st.write("🧠 Retrieving relevant schema using RAG...")

    if "rag" not in st.session_state:
        st.session_state.rag = RAGPipeline(full_schema)

    rag = st.session_state.rag
    relevant_schema = rag.retrieve(question)

    steps["relevant_schema"] = relevant_schema
    progress.progress(40)

    # ================= 🔥 RETRY LOOP =================
    MAX_RETRIES = 2
    feedback = ""
    final_df = None
    final_sql = None

    for attempt in range(MAX_RETRIES):

        st.write(f"🤖 Attempt {attempt + 1}")

        # ===== GENERATE =====
        raw_sql = generate_sql(question + feedback, relevant_schema)
        cleaned_sql = clean_sql(raw_sql)

        steps["raw_sql"] = raw_sql
        steps["generated_sql"] = cleaned_sql

        progress.progress(60)

        # ===== VALIDATE =====
        is_valid, parsed = validate_sql(cleaned_sql)

        if not is_valid:
            feedback = f"\nFix SQL syntax error: {parsed}"
            continue

        steps["parsed_sql"] = str(parsed)
        steps["tables"] = extract_tables(parsed)
        steps["columns"] = extract_columns(parsed)
        steps["query_type"] = type(parsed).__name__

        # ===== SAFETY =====
        if not is_safe(cleaned_sql):
            st.error("🚫 Unsafe query detected!")
            st.stop()

        # ===== EXECUTE =====
        try:
            rows, columns = execute_query(cursor, cleaned_sql)
            df = pd.DataFrame(rows, columns=columns)
        except Exception as e:
            feedback = f"\nFix this SQL error: {str(e)}"
            continue

        # ===== EMPTY RESULT CHECK 🔥 =====
        if df.empty:
            feedback = "\nQuery returned no results. Avoid unnecessary JOINs."
            continue

        # ===== INTENT CHECK 🔥 =====
        intent_result = check_intent(question, cleaned_sql)

        if not intent_result.get("is_correct", True):
            issue = intent_result.get("issue", "")
            st.warning(f"⚠️ Intent Issue: {issue}")

            feedback = f"\nFix this issue: {issue}"
            continue

        # ✅ SUCCESS
        final_df = df
        final_sql = cleaned_sql
        steps["result"] = df
        break

    progress.progress(100)

    # ================= UI =================

    tab1, tab2, tab3 = st.tabs(["📊 Result", "🧠 SQL", "🐞 Debug"])

    # ===== RESULT =====
    with tab1:
        st.subheader("📊 Query Result")
        if final_df is not None:
            st.dataframe(final_df, use_container_width=True)
        else:
            st.error("❌ Failed after retries")

    # ===== SQL =====
    with tab2:
        st.subheader("🧠 Final SQL")
        st.code(final_sql or "No SQL generated", language="sql")

    # ===== DEBUG =====
    with tab3:

        with st.expander("📦 Full Schema"):
            st.text(steps.get("full_schema", ""))

        with st.expander("🎯 RAG Schema"):
            st.text(steps.get("relevant_schema", ""))

        with st.expander("🧾 Raw SQL"):
            st.code(steps.get("raw_sql", ""), language="sql")

        with st.expander("🧠 SQLGlot Analysis"):
            st.code(steps.get("parsed_sql", ""), language="sql")

            st.write("📊 Tables:", steps.get("tables", []))
            st.write("📄 Columns:", steps.get("columns", []))

    # ================= SIDEBAR =================
    st.sidebar.title("🧾 Debug Logs")
    st.sidebar.write("Query:", question)
    st.sidebar.code(final_sql or "", language="sql")

    cursor.close()
    conn.close()
