import streamlit as st
import pandas as pd
import time

from db.connection import get_connection
from db.executor import execute_query
from llm.generator import generate_sql
from utils.schema import get_schema, get_foreign_keys
from rag.rag_pipeline import RAGPipeline

from utils.validator import is_safe, validate_sql, extract_tables, extract_columns
from correction.intent_checker import check_intent
from utils.join_graph import build_join_graph, get_relevant_joins


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
st.title("🧠 NeuroQuery - NLP to SQL (Self-Correcting + Join-Aware)")

question = st.text_input("💬 Ask your query:")


if question:

    steps = {}
    progress = st.progress(0)

    conn = get_connection()
    cursor = conn.cursor()

    # ================= SCHEMA =================
    st.write("🔍 Fetching schema...")
    full_schema = get_schema(cursor)
    progress.progress(20)

    # ================= JOIN GRAPH =================
    relationships = get_foreign_keys(cursor)
    join_graph = build_join_graph(relationships)

    # ================= RAG =================
    st.write("🧠 Retrieving relevant schema using RAG...")

    if "rag" not in st.session_state:
        st.session_state.rag = RAGPipeline(full_schema)

    rag = st.session_state.rag
    relevant_schema = rag.retrieve(question)
    progress.progress(40)

    # ================= JOIN CONTEXT =================
    from utils.join_path_finder import (
        find_multi_join_path,
        format_join_path,
        extract_tables_from_schema
    )

    # extract tables from RAG
    tables = extract_tables_from_schema(relevant_schema)

    # find optimal path
    join_path = find_multi_join_path(join_graph, tables)

    # format for LLM
    join_context = format_join_path(join_path)

    # ================= RETRY LOOP (FIXED UX) =================
    MAX_RETRIES = 3
    feedback = ""
    final_df = None
    final_sql = None

    status_box = st.empty()
    log_box = st.container()

    with st.spinner("🤖 Thinking..."):

        for attempt in range(MAX_RETRIES):

            status_box.info(f"🤖 Attempt {attempt + 1}")

            # ===== GENERATE =====
            raw_sql = generate_sql(question + feedback, relevant_schema, join_context)
            cleaned_sql = clean_sql(raw_sql)

            with log_box:
                st.markdown(f"### 🔹 Attempt {attempt + 1}")
                st.code(cleaned_sql, language="sql")

            progress.progress(60)

            # ===== VALIDATE =====
            is_valid, parsed = validate_sql(cleaned_sql)

            if not is_valid:
                feedback = f"\nFix SQL syntax error: {parsed}"
                with log_box:
                    st.warning(f"❌ Syntax Error: {parsed}")
                continue

            # ===== SAFETY FIX (IMPORTANT) =====
            if not is_safe(cleaned_sql):
                feedback = "\nQuery used DELETE/UPDATE. Convert it to SELECT."
                with log_box:
                    st.warning("🚫 Unsafe query → converting to SELECT")
                continue

            # ===== EXECUTE =====
            try:
                rows, columns = execute_query(cursor, cleaned_sql)
                df = pd.DataFrame(rows, columns=columns)
            except Exception as e:
                feedback = f"\nFix this SQL error: {str(e)}"
                with log_box:
                    st.error(f"❌ Execution Error: {str(e)}")
                continue

            # ===== EMPTY RESULT =====
            if df.empty:
                feedback = "\nQuery returned no results. Avoid unnecessary JOINs."
                with log_box:
                    st.warning("⚠️ Empty result → retrying")
                continue

            # ===== INTENT CHECK =====
            intent_result = check_intent(question, cleaned_sql)

            if not intent_result.get("is_correct", True):
                issue = intent_result.get("issue", "")
                feedback = f"\nFix this issue: {issue}"

                with log_box:
                    st.warning(f"⚠️ Intent Issue: {issue}")
                continue

            # ✅ SUCCESS
            final_df = df
            final_sql = cleaned_sql

            with log_box:
                st.success("✅ Query successful")

            break

            time.sleep(0.3)  # small delay for UX feel

    progress.progress(100)
    status_box.success("✅ Completed")

    # ================= OUTPUT =================

    tab1, tab2, tab3 = st.tabs(["📊 Result", "🧠 SQL", "🐞 Debug"])

    with tab1:
        st.subheader("📊 Query Result")
        if final_df is not None:
            st.dataframe(final_df, use_container_width=True)
        else:
            st.error("❌ Failed after retries")

    with tab2:
        st.subheader("🧠 Final SQL")
        st.code(final_sql or "No SQL generated", language="sql")

    with tab3:

        with st.expander("📦 Full Schema"):
            st.text(full_schema)

        with st.expander("🎯 RAG Schema"):
            st.text(relevant_schema)

        with st.expander("🔗 Join Context"):
            st.text(join_context)

    # ================= SIDEBAR =================
    st.sidebar.title("🧾 Debug Logs")
    st.sidebar.write("Query:", question)
    st.sidebar.code(final_sql or "", language="sql")

    cursor.close()
    conn.close()
