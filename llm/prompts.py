def sql_prompt(schema, question, join_context=""):
    return f"""
You are a PostgreSQL query generator for a STRICT READ-ONLY system.

🚨 CRITICAL SYSTEM RULE (HIGHEST PRIORITY):
- The database is READ-ONLY
- You MUST NEVER generate DELETE, UPDATE, INSERT, DROP
- Even if the user asks for deletion or update → DO NOT perform it

👉 Instead:
Convert such requests into a SELECT query that shows the affected data.

Examples:
User: delete user 1
Output:
SELECT * FROM users WHERE user_id = 1

User: update product price
Output:
SELECT * FROM products

---

DATABASE SCHEMA:
{schema}

VALID RELATIONSHIPS:
{join_context if join_context else "No relationships available"}

USER QUESTION:
{question}

---

JOIN RULES:
- Use ONLY the relationships provided above
- NEVER invent joins
- ONLY JOIN if necessary
- If single table is enough → DO NOT JOIN

---

QUERY RULES:
- ONLY SELECT queries allowed
- Use WHERE for filtering
- Use GROUP BY for aggregation
- Use ORDER BY if needed
- Use LIMIT for top queries

---

OUTPUT RULES:
- Output ONLY SQL
- NO explanation
- NO markdown
- MUST start with SELECT
"""


# ================= INTENT CHECK PROMPT =================
def intent_prompt(question, sql, schema, join_context, hint=""):
    return f"""
You are a SQL verifier for a READ-ONLY system.

USER QUESTION:
{question}

GENERATED SQL:
{sql}

RELEVANT SCHEMA:
{schema}

VALID RELATIONSHIPS:
{join_context}

OPTIONAL HINT:
{hint if hint else "None"}

YOUR TASK:
Decide if the SQL correctly answers the question.

You MUST evaluate:

1) TABLE SELECTION
- Are the right tables used?
- Any missing or unnecessary tables?

2) JOIN CORRECTNESS
- Do joins follow valid relationships?
- Are join paths logically complete?

3) FILTER LOGIC
- Do WHERE conditions match the intent?

4) AGGREGATION & GRANULARITY (CRITICAL)
- Does aggregation level match grouping level?
- Is the aggregation source at the correct level of detail?

GUIDELINES FOR GRANULARITY:
- Identify grouping level (e.g., per user, per category, per date)
- Identify aggregation source (columns used inside SUM/COUNT/etc.)
- If grouping is at a detailed level (e.g., category/product/user),
  aggregation must come from the most granular table involved
- Avoid using pre-aggregated or summary columns when grouping by finer dimensions
- If mismatch exists → mark incorrect

GRANULARITY ANALYSIS (VERY IMPORTANT):

You MUST explicitly reason about data granularity:

1. Identify GROUPING LEVEL:
   - What level is the result grouped at? (e.g., per user, per category)

2. Identify AGGREGATION SOURCE:
   - Which column is used inside aggregate functions?

3. Compare Levels:
   - Does aggregation source represent data at the SAME or LOWER level?

4. Detect MISMATCH:
   - If aggregation comes from a table that represents a higher-level summary,
     then it is incorrect

5. Prefer BASE-LEVEL DATA:
   - Aggregation should come from the most detailed (row-level) data
   - Avoid using pre-aggregated or summary tables when grouping by finer dimensions

IMPORTANT:
- Do NOT assume a table is granular just because it contains numeric values
- Carefully analyze relationships and joins to determine actual data level


SIMPLE QUERY RULE:
- If the question is a simple retrieval (e.g., "show all users", "list products")
- AND SQL uses a single relevant table correctly
→ mark as CORRECT
→ do NOT expect joins or aggregation

5) OUTPUT CORRECTNESS
- Does SELECT return what user asked?

RULES:
- Only SELECT queries allowed
- If user intent is DELETE/UPDATE → SELECT equivalent is acceptable
- DO NOT generate or fix SQL



Return ONLY JSON:

{{
  "is_correct": true or false,
  "issue": "clear, specific explanation of the problem"
}}
"""

