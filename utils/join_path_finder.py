from collections import deque


# ================= FIND PATH BETWEEN 2 TABLES =================
def find_join_path(graph, start, end):
    """
    BFS to find shortest join path between two tables
    """

    queue = deque([(start, [])])
    visited = set()

    while queue:
        current, path = queue.popleft()

        if current == end:
            return path

        if current in visited:
            continue

        visited.add(current)

        for neighbor in graph.get(current, []):
            next_table = neighbor["table"]
            condition = neighbor["condition"]

            queue.append(
                (next_table, path + [(current, next_table, condition)])
            )

    return []


# ================= MULTI-TABLE PATH =================
def find_multi_join_path(graph, tables):
    """
    Connect multiple tables into a join path
    """

    if len(tables) <= 1:
        return []

    full_path = []

    for i in range(len(tables) - 1):
        path = find_join_path(graph, tables[i], tables[i + 1])
        full_path.extend(path)

    return full_path


# ================= FORMAT FOR LLM =================
def format_join_path(join_path):
    """
    Convert path into join conditions string
    """

    conditions = []

    for _, _, condition in join_path:
        conditions.append(condition)

    return "\n".join(set(conditions))


# ================= EXTRACT TABLES =================
def extract_tables_from_schema(relevant_schema):
    """
    Extract table names from RAG output
    """

    tables = set()

    for line in relevant_schema.split("\n"):
        if "." in line:
            tables.add(line.split(".")[0])

    return list(tables)
