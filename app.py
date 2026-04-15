import streamlit as st
import pandas as pd
from db.connection import get_connection
from db.executor import execute_query
from llm.generator import generate_sql
from utils.schema import get_schema
from utils.validator import is_safe
from rag.rag_pipeline import RAGPipeline   # ✅ RAG import


# ================= CLEAN SQL =================
def clean_sql(sql):
    sql = sql.strip()

    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()

    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    return sql


# ================= UI CONFIG =================
st.set_page_config(page_title="NeuroQuery", layout="wide")
st.title("🧠 NeuroQuery - NLP to SQL (RAG Enabled)")

# ================= INPUT =================
question = st.text_input("💬 Ask your query:")

# ================= MAIN =================
if question:

    steps = {}
    progress = st.progress(0)

    # ================= STEP 1: SCHEMA =================
    st.write("🔍 Fetching schema...")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        full_schema = get_schema(cursor)
        steps["full_schema"] = full_schema
        progress.progress(20)
    except Exception as e:
        st.error(f"Schema Error: {e}")
        st.stop()

    # ================= STEP 2: RAG =================
    st.write("🧠 Retrieving relevant schema using RAG...")

    if "rag" not in st.session_state:
        st.write("🔥 FULL SCHEMA:", full_schema)
        st.session_state.rag = RAGPipeline(full_schema)

    rag = st.session_state.rag
    relevant_schema = rag.retrieve(question)

    steps["relevant_schema"] = relevant_schema
    progress.progress(40)

    # ================= STEP 3: SQL GENERATION =================
    st.write("🤖 Generating SQL...")

    try:
        raw_sql = generate_sql(question, relevant_schema)
        cleaned_sql = clean_sql(raw_sql)

        steps["raw_sql"] = raw_sql
        steps["generated_sql"] = cleaned_sql

        progress.progress(60)

    except Exception as e:
        st.error(f"LLM Error: {e}")
        st.stop()

    # ================= STEP 4: VALIDATION =================
    safe = is_safe(cleaned_sql)
    steps["is_safe"] = safe
    progress.progress(80)

    if not safe:
        st.error("🚫 Unsafe query detected!")
        st.stop()

    # ================= STEP 5: EXECUTION =================
    try:
        rows, columns = execute_query(cursor, cleaned_sql)
        df = pd.DataFrame(rows, columns=columns)
        steps["result"] = df
        progress.progress(100)
    except Exception as e:
        steps["error"] = str(e)

    # ================= UI DISPLAY =================

    tab1, tab2, tab3 = st.tabs(["📊 Result", "🧠 SQL", "🐞 Debug"])

    # ===== RESULT =====
    with tab1:
        st.subheader("📊 Query Result")
        if "result" in steps:
            st.dataframe(steps["result"], use_container_width=True)
        else:
            st.warning("No result found")

    # ===== SQL =====
    with tab2:
        st.subheader("🧠 Cleaned SQL (Executed)")
        st.code(steps.get("generated_sql", ""), language="sql")

    # ===== DEBUG =====
    with tab3:

        with st.expander("📦 Full Schema"):
            st.text(steps.get("full_schema", ""))

        with st.expander("🎯 RAG Retrieved Schema"):
            st.text(steps.get("relevant_schema", ""))

        with st.expander("🧾 Raw LLM Output"):
            st.code(steps.get("raw_sql", ""), language="sql")

        with st.expander("🧠 Cleaned SQL"):
            st.code(steps.get("generated_sql", ""), language="sql")

        with st.expander("🛡️ Safety Check"):
            st.write("Safe Query:", steps.get("is_safe"))

        with st.expander("❌ Errors"):
            if "error" in steps:
                st.error(steps["error"])
            else:
                st.success("No errors 🎉")

    # ================= SIDEBAR =================
    st.sidebar.title("🧾 Debug Logs")
    st.sidebar.write("User Query:", question)
    st.sidebar.write("Safe:", steps.get("is_safe", ""))

    st.sidebar.markdown("### 🧠 SQL")
    st.sidebar.code(steps.get("generated_sql", ""), language="sql")

    # Close connection
    cursor.close()
    conn.close()