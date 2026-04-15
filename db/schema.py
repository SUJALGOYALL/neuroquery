def get_schema(cursor):
    cursor.execute("""
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public';
    """)

    rows = cursor.fetchall()

    schema_dict = {}

    for table, column in rows:
        if table not in schema_dict:
            schema_dict[table] = []
        schema_dict[table].append(column)

    return schema_dict


def format_schema(schema_dict):
    schema_str = ""

    for table, columns in schema_dict.items():
        cols = ", ".join(columns)
        schema_str += f"{table}({cols}) "

    return schema_str.strip()


def get_foreign_keys(cursor):
    cursor.execute("""
    SELECT
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table,
        ccu.column_name AS foreign_column
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY';
    """)

    return cursor.fetchall()