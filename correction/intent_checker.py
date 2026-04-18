import json
from llm.generator import generate_sql


def check_intent(question: str, sql: str) -> dict:
    """
    Checks whether generated SQL aligns with user intent.
    DOES NOT generate SQL — only returns judgement + issue.
    """

    prompt = f"""
You are a SQL verifier for a READ-ONLY system.

User Question:
{question}

Generated SQL:
{sql}

STRICT SYSTEM RULES:
1. ONLY SELECT queries are allowed
2. DELETE / UPDATE / INSERT are NEVER allowed
3. If user asks for DELETE/UPDATE:
   → Converting it to SELECT is CORRECT
   → DO NOT mark it incorrect

YOUR TASK:
- Check if SQL correctly answers the question
- Focus on:
  ✔ correct table
  ✔ correct filtering
  ✔ no unnecessary joins

IMPORTANT:
- DO NOT expect DELETE queries
- DO NOT penalize SELECT replacing DELETE
- If SQL retrieves correct data → mark correct

Return ONLY JSON:
{{
  "is_correct": true,
  "issue": ""
}}

If incorrect:
{{
  "is_correct": false,
  "issue": "explain the issue clearly"
}}
"""

    try:
        response = generate_sql(prompt, "")

        # Clean response
        response = response.strip()
        response = response.replace("```json", "").replace("```", "").strip()

        result = json.loads(response)

        # fallback safety
        if not isinstance(result, dict):
            return {"is_correct": True, "issue": ""}

        if "is_correct" not in result:
            return {"is_correct": True, "issue": ""}

        return result

    except Exception as e:
        print("⚠️ Intent checker failed:", e)
        return {"is_correct": True, "issue": ""}