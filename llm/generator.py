from llm.groq_client import client
from llm.prompts import sql_prompt


# ================= CLEAN SQL =================
def clean_sql(sql: str) -> str:
    sql = sql.strip()

    # Remove markdown blocks ```sql ... ```
    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()

    # Remove leading "sql" word if present
    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    return sql


# ================= GENERATE SQL =================
def generate_sql(question, schema):
    prompt = sql_prompt(schema, question)

    # 🔥 Add strict instructions (VERY IMPORTANT)
    strict_rules = """
STRICT RULES:
- Only return SQL query
- No markdown (no ``` )
- No explanation
- No comments
- Do NOT start with 'sql'
- Query must be valid PostgreSQL
- Only SELECT queries allowed
"""

    final_prompt = prompt + "\n" + strict_rules

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # ✅ safer + faster for you
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0
        )

        raw_sql = response.choices[0].message.content

        # ✅ Clean at backend
        cleaned_sql = clean_sql(raw_sql)

        return cleaned_sql

    except Exception as e:
        raise Exception(f"LLM Generation Failed: {e}")