import sqlglot
from sqlglot import exp


# BASIC SAFETY CHECK (IMPROVED)
def is_safe(query: str) -> bool:
    """
    Allow only SELECT queries (strict)
    """
    try:
        parsed = sqlglot.parse_one(query)
        return isinstance(parsed, exp.Select)
    except:
        return False


# SQL VALIDATION
def validate_sql(query: str):
    """
    Validate SQL syntax and structure
    Returns (is_valid, parsed_or_error)
    """
    try:
        parsed = sqlglot.parse_one(query)

        # Only allow SELECT
        if not isinstance(parsed, exp.Select):
            return False, "Only SELECT queries allowed"

        return True, parsed

    except Exception as e:
        return False, str(e)


# EXTRACT TABLES
def extract_tables(parsed):
    return [t.name for t in parsed.find_all(exp.Table)]


# EXTRACT COLUMNS
def extract_columns(parsed):
    return [c.name for c in parsed.find_all(exp.Column)]