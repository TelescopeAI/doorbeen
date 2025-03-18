def db_assistant_summarizer(summarized_results: str):
    prompt = f"""Given the summarized SQL query results: {summarized_results}
                        Provide:
                        1. A text analysis with insights (key 'text_content')
                        2. If relevant, a description of a table to show (key 'table_description')
                        3. If relevant, a description of a chart to create (key 'chart_description')
                        
                        Respond in valid JSON format with these keys."""
    return prompt

def db_query_validator():
    prompt = """You are a SQL expert with a strong attention to detail.
Double check the SQLite query for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

You will call the appropriate tool to execute the query after running this check."""
    return prompt




