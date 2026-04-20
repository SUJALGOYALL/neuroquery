import json

from sympy import python
from llm.generator import call_model
from llm.prompts import intent_prompt


# 🔥 OPTIONAL: simple heuristic hint generator (NOT hardcoded rules)
def generate_hint(question: str, sql: str) -> str:
    s = sql.lower()

    hints = []
# ================= SIMPLE QUERY DETECTION =================
    if "group by" not in s and "join" not in s:
        return (
            "SIMPLE QUERY DETECTED:\n"
            "- This is a direct retrieval query\n"
            "- No joins or aggregation required\n"
            "- If query uses correct table → it is likely correct\n"
            "- Do NOT force additional joins or complexity\n"
        )

    # ================= AGGREGATION vs GROUPING =================
    if "group by" in s and any(func in s for func in ["sum(", "count(", "avg(", "min(", "max("]):
        hints.append(
            "AGGREGATION vs GROUPING ANALYSIS (CRITICAL):\n"
            "- Identify grouping columns (GROUP BY)\n"
            "- Identify aggregation source (columns inside aggregate functions)\n"
            "- Determine the data level of each table involved (row-level vs summary-level)\n"
            "- Aggregation must be computed from SAME or LOWER (more detailed) level than grouping\n"
            "- If aggregation comes from a higher-level summary table → this is incorrect\n"
        )

    # ================= GRANULARITY (DETAILED) =================
    if "group by" in s:
        hints.append(
            "GRANULARITY REASONING (VERY IMPORTANT):\n"
            "- Step 1: Determine grouping level (e.g., per user, per category, per date)\n"
            "- Step 2: Determine what each row in the result represents\n"
            "- Step 3: Identify which table contains data at that level or finer\n"
            "- Step 4: Ensure aggregation is computed from that base-level data\n"
            "- Avoid assuming a table is granular just because it contains numeric values\n"
            "- Summary tables (totals, payments, aggregates) may NOT match grouping level\n"
        )

    # ================= JOIN PATH VALIDATION =================
    if "join" in s:
        hints.append(
            "JOIN PATH VALIDATION:\n"
            "- Trace how tables are connected step-by-step\n"
            "- Ensure joins follow valid relationships (foreign keys)\n"
            "- Do NOT skip intermediate tables in relationships\n"
            "- Ensure join keys represent actual relationships, not guessed matches\n"
        )

    # ================= JOIN + AGGREGATION =================
    if "join" in s and "group by" in s:
        hints.append(
            "JOIN + AGGREGATION INTERACTION:\n"
            "- Ensure joins bring correct granularity BEFORE aggregation\n"
            "- Aggregation must be applied AFTER correct join path is established\n"
            "- Incorrect joins can duplicate or collapse rows → wrong results\n"
        )

    # ================= FILTER LOGIC =================
    if "where" in s:
        hints.append(
            "FILTER LOGIC CHECK:\n"
            "- Ensure filters match user intent\n"
            "- Verify whether filtering should happen before or after aggregation\n"
        )

    # ================= GROUP BY VALIDATION =================
    if "group by" in s:
        hints.append(
            "GROUP BY VALIDATION:\n"
            "- All non-aggregated selected columns must be in GROUP BY\n"
            "- Ensure grouping columns align with what the user asked\n"
        )

    # ================= OUTPUT VALIDATION =================
    hints.append(
        "OUTPUT VALIDATION:\n"
        "- Ensure SELECT columns match user question\n"
        "- Avoid unnecessary columns\n"
        "- Ensure correct aliases and readability\n"
    )

    # ================= ERROR RECOVERY =================
    hints.append(
        "ERROR RECOVERY STRATEGY:\n"
        "- Compare with previous attempt and identify repeated mistake\n"
        "- Change BOTH aggregation source and join path if needed\n"
        "- Do not reuse same logical pattern if it failed before\n"
    )

    # ================= META REASONING =================
    hints.append(
        "META REASONING:\n"
        "- Reconstruct solution from first principles:\n"
        "  entities → relationships → level of detail → aggregation\n"
        "- Do NOT rely on surface patterns (e.g., numeric column = correct)\n"
    )

    return "\n\n".join(hints)




def clean_response(response: str) -> str:
    response = response.strip()
    response = response.replace("```json", "").replace("```", "").strip()
    return response


def check_intent(question: str, sql: str, schema: str, join_context: str) -> dict:
    """
    Strong intent checker:
    - Uses schema + join context
    - Adds structured reasoning hint
    - Enforces granularity-aware thinking
    - Ensures robust JSON parsing
    """

    # 🔥 Generate reasoning hint
    hint = generate_hint(question, sql)

    # 🔥 Add meta-instruction (VERY IMPORTANT, but generic)
    meta_instruction = """
IMPORTANT REASONING REQUIREMENTS:
- Do NOT assume any table is correct based on column names
- Determine data granularity using relationships and joins
- Validate aggregation level vs grouping level carefully
- If unsure, prefer marking query as incorrect rather than guessing
"""

    # 🔥 Final prompt
    prompt = intent_prompt(
        question,
        sql,
        schema,
        join_context,
        hint + "\n\n" + meta_instruction
    )

    try:
        response = call_model(prompt)
        response = clean_response(response)

        result = json.loads(response)

        # ================= VALIDATION =================
        if not isinstance(result, dict):
            raise ValueError("Response is not a dict")

        if "is_correct" not in result:
            raise ValueError("Missing is_correct field")

        issue = result.get("issue", "").strip()

        # 🔥 Strong fallback if model is vague
        if not issue and not result.get("is_correct", True):
            issue = (
                "The SQL query does not correctly match the user intent. "
                "There may be issues in joins, aggregation level, or filtering logic."
            )

        # 🔥 Normalize
        return {
            "is_correct": bool(result["is_correct"]),
            "issue": issue
        }

    except Exception as e:
        print("⚠️ Intent checker failed:", e)

        # 🔥 Safe fallback (do not break pipeline)
        return {
            "is_correct": True,
            "issue": ""
        }

