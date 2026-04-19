from db.connection import get_connection
from rag.rag_pipeline import RAGPipeline
from utils.schema import get_schema, get_primary_keys, get_foreign_keys

# 🔥 Graph
from agent.sql_agent import build_graph

# 🔥 JOIN GRAPH
from utils.join_graph import build_join_graph, get_relevant_joins

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

    # ================= JOIN GRAPH =================
    join_graph = build_join_graph(relationships)

    # ================= RAG =================
    if rag_instance is None:
        rag_instance = RAGPipeline(full_schema, relationships, primary_keys)

    relevant_schema = rag_instance.retrieve(question)
    print("\nRAG Schema:\n", relevant_schema)

    # ================= FILTER JOINS =================
    join_context = get_relevant_joins(join_graph, relevant_schema)

    print("\nJoin Context:\n", join_context)

    # ================= COMBINE CONTEXT =================
    enhanced_schema = (
        relevant_schema
        + "\n\nValid Relationships:\n"
        + (join_context if join_context else "No relationships found")
    )

    # ================= LANGGRAPH =================
    graph = build_graph()

    state = {
        "question": question,
        "schema": enhanced_schema,  # 🔥 IMPORTANT FIX
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



# ================= graph =================
from agent.sql_agent import build_graph

graph = build_graph()

print("\n🧠 AGENT GRAPH:\n")
print(graph.get_graph().print_ascii())

if __name__ == "__main__":
    main()

