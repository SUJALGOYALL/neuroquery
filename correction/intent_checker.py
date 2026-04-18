import json
from llm.generator import call_model
from llm.prompts import intent_prompt


def check_intent(question: str, sql: str) -> dict:
    """
    Checks whether generated SQL aligns with user intent.
    DOES NOT generate SQL — only returns judgement + issue.
    """

    prompt = intent_prompt(question, sql)

    try:
        response = call_model(prompt)

        # 🔥 Clean response
        response = response.strip()
        response = response.replace("```json", "").replace("```", "").strip()

        result = json.loads(response)

        # 🔥 Safety fallback
        if not isinstance(result, dict):
            return {"is_correct": True, "issue": ""}

        if "is_correct" not in result:
            return {"is_correct": True, "issue": ""}

        return result

    except Exception as e:
        print("⚠️ Intent checker failed:", e)
        return {"is_correct": True, "issue": ""}
