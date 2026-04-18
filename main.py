from db.connection import get_connection
from rag.rag_pipeline import RAGPipeline
from utils.schema import get_schema, get_primary_keys, get_foreign_keys

# 🔥 NEW: import graph
from agent.sql_agent import build_graph


rag_instance = None  # global


def main():
    global rag_instance

    conn = get_connection()
    cursor = conn.cursor()

    question = input("Ask your query: ")

    # ================= SCHEMA =================
    full_schema = get_schema(cursor)
    relationships = get_foreign_keys(cursor)
    primary_keys = get_primary_keys(cursor)

    print("\nFull Schema:\n", full_schema)

    # ================= RAG =================
    if rag_instance is None:
        rag_instance = RAGPipeline(full_schema, relationships, primary_keys)

    relevant_schema = rag_instance.retrieve(question)
    print("\nRAG Schema:\n", relevant_schema)

    # ================= LANGGRAPH =================
    graph = build_graph()

    state = {
        "question": question,
        "schema": relevant_schema,
        "sql": None,
        "feedback": "",
        "df": None,
        "error": None,
        "attempt": 0,
        "cursor": cursor
    }

    result = graph.invoke(state)

    # ================= OUTPUT =================
    if result.get("error"):
        print("❌ Error:", result["error"])

    elif result.get("df") is not None:
        print("\nFinal SQL:\n", result.get("sql"))

        print("\nResults:\n")
        for row in result["df"].values:
            print(row)

    else:
        print("❌ Failed to generate correct SQL after retries.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()