import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


class RAGPipeline:
    def __init__(self, schema, relationships=None, primary_keys=None):
        print("🔹 Initializing RAG Pipeline...")

        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.relationships = relationships or []
        self.primary_keys = primary_keys or []

        # Build documents
        self.docs = self.build_schema_docs(schema)

        print("\n📄 Generated Schema Docs:")
        for d in self.docs:
            print("   ", d)

        if not self.docs:
            print("❌ DEBUG - SCHEMA INPUT:", schema)
            raise ValueError("No schema docs found. Check schema format.")

        # Create embeddings
        self.embeddings = self.model.encode(self.docs)
        self.embeddings = np.array(self.embeddings)

        if len(self.embeddings.shape) == 1:
            self.embeddings = self.embeddings.reshape(1, -1)

        print("\n📐 Embedding Shape:", self.embeddings.shape)

        # FAISS index
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(self.embeddings)

        print("✅ FAISS index created successfully!")

    # -----------------------------
    # BUILD SCHEMA DOCS
    # -----------------------------
    def build_schema_docs(self, schema):
        docs = []

        print("\n🧠 Raw schema received:", schema)

        # -------- CASE 1: STRING --------
        if isinstance(schema, str):
            tables = schema.split(")")

            for table in tables:
                table = table.strip()
                if not table:
                    continue

                if "(" in table:
                    table_name, columns_part = table.split("(", 1)

                    table_name = table_name.strip()
                    columns = [c.strip() for c in columns_part.split(",") if c.strip()]

                    for col in columns:
                        docs.append(f"{table_name}.{col}")

        # -------- CASE 2: DICT --------
        elif isinstance(schema, dict):
            for table, columns in schema.items():
                for col in columns:
                    docs.append(f"{table}.{col}")

        # -------- CASE 3: LIST --------
        elif isinstance(schema, list):
            for row in schema:

                if isinstance(row, tuple) and len(row) >= 2:
                    table, column = row[0], row[1]

                elif isinstance(row, dict):
                    table = row.get("table_name")
                    column = row.get("column_name")

                else:
                    continue

                if table and column:
                    docs.append(f"{table}.{column}")

        # -------- ADD RELATIONSHIPS --------
        print("\n🔗 Adding relationships...")

        for rel in self.relationships:
            try:
                src_table, src_col, tgt_table, tgt_col = rel
                docs.append(f"{src_table}.{src_col} = {tgt_table}.{tgt_col}")
            except:
                continue

        print("\n✅ Final docs:", docs)

        return docs

        # -------- ADD PRIMARY KEYS --------
        print("\n🔑 Adding primary keys...")

        for pk in self.primary_keys:
            try:
                table, column = pk
                docs.append(f"{table}.{column} is primary key")
            except:
                continue

    # -----------------------------
    # RETRIEVE RELEVANT CONTEXT
    # -----------------------------
    def retrieve(self, query, k=12):
        print("\n🔍 Query:", query)

        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding)

        distances, indices = self.index.search(query_embedding, k)

        print("📊 Retrieved indices:", indices)

        # Initial results
        results = [self.docs[i] for i in indices[0]]

        # -----------------------------
        # 🔥 TABLE EXPANSION LOGIC
        # -----------------------------
        tables = set([r.split('.')[0] for r in results if '.' in r])

        expanded_results = []

        for doc in self.docs:
            if any(doc.startswith(table + ".") for table in tables):
                expanded_results.append(doc)

        results = list(set(results + expanded_results))

        # -----------------------------
        # 🔥 INCLUDE RELATIONSHIPS ALWAYS
        # -----------------------------
        relationship_docs = [doc for doc in self.docs if "=" in doc]
        results = list(set(results + relationship_docs))

        print("\n📄 Final Retrieved Docs:")
        for r in results:
            print("   ", r)

        return "\n".join(results)