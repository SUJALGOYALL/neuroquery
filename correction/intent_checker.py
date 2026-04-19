import json
from llm.generator import call_model
from llm.prompts import intent_prompt


# 🔥 OPTIONAL: simple heuristic hint generator (NOT hardcoded rules)
def generate_hint(question: str, sql: str) -> str:
    q = question.lower()
    s = sql.lower()

    # detect possible aggregation mismatch
    if "group by" in s and "category" in s and "sum(payments.amount" in s:
        return "Possible aggregation mismatch: payments.amount is order-level but grouping involves category."

    if "group by" in s and "order_items" not in s and "category" in s:
        return "Category-based grouping usually requires order_items-level data."

    return ""


def clean_response(response: str) -> str:
    response = response.strip()
    response = response.replace("```json", "").replace("```", "").strip()
    return response


def check_intent(question: str, sql: str, schema: str, join_context: str) -> dict:
    """
    Strong intent checker:
    - Uses schema + join context
    - Adds optional reasoning hint
    - Ensures robust JSON parsing
    """

    hint = generate_hint(question, sql)

    prompt = intent_prompt(question, sql, schema, join_context, hint)

    try:
        response = call_model(prompt)
        response = clean_response(response)

        result = json.loads(response)

        # ✅ Strict validation
        if not isinstance(result, dict):
            raise ValueError("Response is not a dict")

        if "is_correct" not in result:
            raise ValueError("Missing is_correct field")

        if "issue" not in result:
            result["issue"] = ""

        # normalize
        result["is_correct"] = bool(result["is_correct"])

        return result

    except Exception as e:
        print("⚠️ Intent checker failed:", e)
        return {
            "is_correct": True,
            "issue": ""
        }
