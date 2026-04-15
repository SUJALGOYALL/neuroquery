from db.connection import get_connection
from db.executor import execute_query
from llm.generator import generate_sql
from rag.rag_pipeline import RAGPipeline
from utils.validator import is_safe, validate_sql, extract_tables
# ✅ Clean imports (remove duplicates)
from utils.schema import get_schema, get_primary_keys, get_foreign_keys

rag_instance = None   # global


def main():
    global rag_instance

    conn = get_connection()
    cursor = conn.cursor()

    question = input("Ask your query: ")

    # 🔥 Get schema + metadata
    full_schema = get_schema(cursor)
    relationships = get_foreign_keys(cursor)
    primary_keys = get_primary_keys(cursor)

    print("\nFull Schema:\n", full_schema)

    # 🔥 Initialize RAG once (FIXED HERE)
    if rag_instance is None:
        rag_instance = RAGPipeline(full_schema, relationships, primary_keys)

    # 🔥 Retrieve relevant schema
    relevant_schema = rag_instance.retrieve(question)
    print("\nRAG Schema:\n", relevant_schema)

    # 🔥 Generate SQL
    sql_query = generate_sql(question, relevant_schema)
    print("\nGenerated SQL:\n", sql_query)

    # Validate SQL
    is_valid, parsed = validate_sql(sql_query)

    if not is_valid:
        print("❌ SQL Validation Error:", parsed)
        return

    # Extract tables (debug)
    tables = extract_tables(parsed)
    print("📊 Tables used:", tables)

    # Safety check
    if not is_safe(sql_query):
        print("🚫 Unsafe query blocked!")
        return

    # 🔥 Execute
    try:
        rows, columns = execute_query(cursor, sql_query)

        print("\nResults:\n")
        for row in rows:
            print(row)

    except Exception as e:
        print("Error:", e)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()