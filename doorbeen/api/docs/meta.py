class DocsMeta:
    API_GLOBAL_DESCRIPTION = """
    Doorbeen is an intelligent SQL assistant that connects Large Language Models (LLMs) with databases, allowing users to interact with their data using natural language. Ask questions about your data in plain English, and Doorbeen translates them into SQL queries, executes them, and presents the results in a human-readable format.
    Currently supported databases are PostgreSQL, MySQL, Oracle, SQLite, and BigQuery.    
    """

    TAGS_META = [
        {
            "name": "Assistants",
            "description": "Endpoints for interacting with AI assistants, including querying databases with natural language, managing assistant state, and retrieving conversation history",
        },
    ]
