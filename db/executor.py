def execute_query(cursor, query):
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        return rows, cols
    except Exception as e:
        cursor.connection.rollback()   # 🔥 ADD THIS
        raise e