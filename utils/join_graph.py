def build_join_graph(fk_rows):
    """
    Builds bidirectional join graph from foreign key rows
    """

    graph = {}

    for child_table, child_col, parent_table, parent_col in fk_rows:

        # forward
        graph.setdefault(child_table, []).append({
            "table": parent_table,
            "condition": f"{child_table}.{child_col} = {parent_table}.{parent_col}"
        })

        # reverse (VERY IMPORTANT)
        graph.setdefault(parent_table, []).append({
            "table": child_table,
            "condition": f"{parent_table}.{parent_col} = {child_table}.{child_col}"
        })

    return graph

def format_join_context(graph):
    """
    Convert join graph to text for LLM prompt
    """

    relations = set()

    for table in graph:
        for edge in graph[table]:
            relations.add(edge["condition"])

    return "\n".join(relations)

def get_relevant_joins(graph, relevant_schema):
    """
    Filter joins only for tables present in RAG schema
    """

    tables = set()

    for line in relevant_schema.split("\n"):
        if "." in line:
            tables.add(line.split(".")[0])

    relations = set()

    for table in tables:
        if table in graph:
            for edge in graph[table]:
                if edge["table"] in tables:
                    relations.add(edge["condition"])

    return "\n".join(relations)

