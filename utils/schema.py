def get_schema(cursor):
    query = """
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position;
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    schema_dict = {}

    for table, column in rows:
        if table not in schema_dict:
            schema_dict[table] = []
        schema_dict[table].append(column)

    schema_text = ""
    for table, columns in schema_dict.items():
        schema_text += f"{table}({', '.join(columns)})\n"

    return schema_text

def get_primary_keys(cursor):
    cursor.execute("""
    SELECT
        kcu.table_name,
        kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'PRIMARY KEY';
    """)
    
    return cursor.fetchall()

def get_foreign_keys(cursor):
    cursor.execute("""
    SELECT
        tc.table_name AS source_table,
        kcu.column_name AS source_column,
        ccu.table_name AS target_table,
        ccu.column_name AS target_column
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY';
    """)
    
    return cursor.fetchall()