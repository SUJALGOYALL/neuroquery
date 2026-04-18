from llm.groq_client import client
from llm.prompts import sql_prompt


# ================= CLEAN SQL =================
def clean_sql(sql: str) -> str:
    sql = sql.strip()

    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()

    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    return sql


# ================= CORE LLM CALL =================
def call_llm(prompt: str) -> str:
    """
    Generic LLM caller (used everywhere)
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You strictly follow instructions and output exactly what is asked."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        raise Exception(f"LLM Call Failed: {e}")


# ================= GENERATE SQL =================
def generate_sql(question, schema, join_context=""):
    """
    SQL generation function
    """

    prompt = sql_prompt(schema, question, join_context)

    # 🔥 Extra enforcement layer
    strict_rules = """
STRICT OUTPUT RULES:
- Return ONLY SQL query
- No markdown (no ``` )
- No explanation
- No comments
- Do NOT start with 'sql'
- Query must be valid PostgreSQL
- ONLY SELECT queries allowed
"""

    final_prompt = prompt + "\n" + strict_rules

    raw_sql = call_llm(final_prompt)

    return clean_sql(raw_sql)


# ================= GENERIC MODEL CALL =================
def call_model(prompt: str) -> str:
    """
    Used for intent checker / future agents
    """
    return call_llm(prompt)
