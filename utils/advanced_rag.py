# utils/advanced_rag.py

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Load embedding model (small + fast)
model = SentenceTransformer("all-MiniLM-L6-v2")


# ================= BUILD DOCUMENTS =================
def build_schema_docs(schema_str):
    """
    Convert schema string into structured documents
    """
    docs = []
    table_map = {}

    for line in schema_str.split("\n"):
        if ":" in line:
            table, column = line.split(":")
            table = table.strip()
            column = column.strip()

            if table not in table_map:
                table_map[table] = []

            table_map[table].append(column)

    for table, cols in table_map.items():
        doc = f"Table {table} has columns: {', '.join(cols)}"
        docs.append(doc)

    return docs


# ================= RAG CLASS =================
class SchemaRAG:
    def __init__(self, docs):
        self.docs = docs

        # Step 1: Convert docs → embeddings
        self.embeddings = model.encode(docs)

        # Step 2: Create FAISS index
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)

        # Step 3: Add embeddings to index
        self.index.add(np.array(self.embeddings))

    def retrieve(self, query, k=3):
        """
        Retrieve top-k relevant schema docs
        """
        # Step 1: Convert query → embedding
        query_embedding = model.encode([query])

        # Step 2: Search in FAISS index
        distances, indices = self.index.search(
            np.array(query_embedding), k
        )

        # Step 3: Get relevant docs
        results = [self.docs[i] for i in indices[0]]

        return "\n".join(results)