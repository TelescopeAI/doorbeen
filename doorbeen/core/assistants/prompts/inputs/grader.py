import json

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate


def grade_question_prompt(schema: str = None):
    prompt = """
        You are provided with the following information:

        - **User's Question**: A question posed by the user.
        - **Database Schema**: A list of table names, each with their columns, data types, and three sample rows of data.

        {schema}

        **Your Task**:

        Evaluate the user's question based on the following criteria:

        1. **Completeness**:

            - **Definition**: Does the question provide all the necessary information to proceed without making assumptions?
            - **Assessment**:
                - Is any crucial detail missing that would prevent accurate execution?
                - Does the question require you to infer or guess any information?
            - **Score**: Assign a score from **1 (very complete)** to **10 (incomplete; requires assumptions)**.

        2. **Relevance**:

            - **Definition**: Does the question reference terms or concepts that exist within the provided database schema?
            - **Assessment**:
                - Are the keywords in the question matching any table names, column names, or data values?
                - Is the question pertinent to the data available?
                - Can this question be answered using the available data?
                - **IMPORTANT**: Consider semantic and conceptual matches, not just exact keyword matches
                - Questions about correlations, trends, or patterns in available data types should be considered relevant
            - **Score**: Assign a score from **1 (highly relevant)** to **10 (not relevant)**.
            - **Scoring Guidelines**:
                - **1-3**: Direct matches or clear conceptual relevance to available data
                - **4-6**: Partial relevance or could be answered with some data interpretation
                - **7-10**: No clear connection to available data types or completely unrelated domain

        3. **Specificity**:

            - **Definition**: How specific is the question in terms of time periods, columns, or combinations of columns?
            - **Assessment**:
                - Does the question narrow down to specific data points or is it broad and general?
                - Are there clear parameters or constraints mentioned?
            - **Score**: Assign a score from **1 (very specific)** to **10 (very vague)**.

        **Overall Grade**:

        - After evaluating the above criteria, assign an **overall grade** to the question:
            - **Grade 1-3**: High quality—complete, relevant, and specific.
            - **Grade 4-6**: Acceptable but could be improved.
            - **Grade 7-10**: Needs significant improvement—incomplete, irrelevant, or vague.

        **Decision on Enrichment**:

        - Set the flag `"should_enrich"` to **true** if the question is RELEVANT to the dataset but lacks specificity or completeness.
        - Set it to **false** if the question is either:
            1. Complete, relevant, and specific enough to proceed as is, OR
            2. Not relevant to the available dataset (cannot be answered with the data)
        
        **CRITICAL RULE**: If the question is relevant to the dataset (relevance score ≤ 6), it should be enriched rather than rejected, even if it's vague or incomplete. Only questions with relevance scores > 6 (clearly irrelevant to the dataset) should be rejected.

        **Examples of Relevant Questions** (should have relevance score ≤ 6):
        - Questions about correlations between data types present in the schema
        - Questions about trends, patterns, or analysis of available data
        - Vague questions that could be answered with available data types
        
        **Examples of Irrelevant Questions** (should have relevance score > 6):
        - Questions about completely different domains (e.g., asking about weather when schema has financial data)
        - Questions requiring data types not present in the schema

        **Output Format**:

        Provide your evaluation in the following JSON format:

            "completeness": 
                "score": <number between 1 and 10>,
                "reason": <short reason for completeness score>,
            "relevance":
                "score": <number between 1 and 10>,
                "reason": <short reason for relevance score>,
            "specificity":
                "score": <number between 1 and 10>,
                "reason": <short reason for specificity score>,
            "overall":
                "score": <number between 1 and 10>,
                "reason": <short reason for the overall grade>,
            "should_enrich": <true or false>,
        """
    template = ChatPromptTemplate([
        ("system", prompt)
    ])
    prompt = template.invoke({
        "schema": schema
    })
    return prompt.to_string()


async def grade_question(question: str, table_schemas, handler):
    """
    Grade a question based on completeness, relevance, and specificity
    """
    # Format the schema information
    schema_info = ""
    for table in table_schemas.tables:
        schema_info += f"Table: {table.name}\n"
        for column in table.columns:
            schema_info += f"  - {column.name}: {column.type}\n"
        schema_info += "\n"
    
    # Create the grading prompt
    prompt = f"""
        You are provided with the following information:

        - **User's Question**: {question}
        - **Database Schema**: A list of table names, each with their columns, data types, and three sample rows of data.

        {schema_info}

        **Your Task**:

        Evaluate the user's question based on the following criteria:

        1. **Completeness**:
            - **Definition**: Does the question provide all the necessary information to proceed without making assumptions?
            - **Assessment**:
                - Is any crucial detail missing that would prevent accurate execution?
                - Does the question require you to infer or guess any information?
            - **Score**: Assign a score from **1 (very complete)** to **10 (incomplete; requires assumptions)**.

        2. **Relevance**:
            - **Definition**: Does the question reference terms or concepts that exist within the provided database schema?
            - **Assessment**:
                - Are the keywords in the question matching any table names, column names, or data values?
                - Is the question pertinent to the data available?
                - Can this question be answered using the available data?
                - **IMPORTANT**: Consider semantic and conceptual matches, not just exact keyword matches
                - Questions about correlations, trends, or patterns in available data types should be considered relevant
            - **Score**: Assign a score from **1 (highly relevant)** to **10 (not relevant)**.
            - **Scoring Guidelines**:
                - **1-3**: Direct matches or clear conceptual relevance to available data
                - **4-6**: Partial relevance or could be answered with some data interpretation
                - **7-10**: No clear connection to available data types or completely unrelated domain

        3. **Specificity**:
            - **Definition**: How specific is the question in terms of time periods, columns, or combinations of columns?
            - **Assessment**:
                - Does the question narrow down to specific data points or is it broad and general?
                - Are there clear parameters or constraints mentioned?
            - **Score**: Assign a score from **1 (very specific)** to **10 (very vague)**.

        **Overall Grade**:
        - After evaluating the above criteria, assign an **overall grade** to the question:
            - **Grade 1-3**: High quality—complete, relevant, and specific.
            - **Grade 4-6**: Acceptable but could be improved.
            - **Grade 7-10**: Needs significant improvement—incomplete, irrelevant, or vague.

        **Decision on Enrichment**:
        - Set the flag `"should_enrich"` to **true** if the question is RELEVANT to the dataset but lacks specificity or completeness.
        - Set it to **false** if the question is either:
            1. Complete, relevant, and specific enough to proceed as is, OR
            2. Not relevant to the available dataset (cannot be answered with the data)
        
        **CRITICAL RULE**: If the question is relevant to the dataset (relevance score ≤ 6), it should be enriched rather than rejected, even if it's vague or incomplete. Only questions with relevance scores > 6 (clearly irrelevant to the dataset) should be rejected.

        **Examples of Relevant Questions** (should have relevance score ≤ 6):
        - Questions about correlations between data types present in the schema
        - Questions about trends, patterns, or analysis of available data
        - Vague questions that could be answered with available data types
        
        **Examples of Irrelevant Questions** (should have relevance score > 6):
        - Questions about completely different domains (e.g., asking about weather when schema has financial data)
        - Questions requiring data types not present in the schema

        **Output Format**:
        Provide your evaluation in the following JSON format:
        {{
            "completeness": {{
                "score": <number between 1 and 10>,
                "reason": "<short reason for completeness score>"
            }},
            "relevance": {{
                "score": <number between 1 and 10>,
                "reason": "<short reason for relevance score>"
            }},
            "specificity": {{
                "score": <number between 1 and 10>,
                "reason": "<short reason for specificity score>"
            }},
            "overall": {{
                "score": <number between 1 and 10>,
                "reason": "<short reason for the overall grade>"
            }},
            "should_enrich": <true or false>
        }}
        """
    
    # Create messages for the LLM
    messages = [
        SystemMessage(content=prompt)
    ]
    
    # Use JSON mode for structured output
    json_llm = handler.model.bind(response_format={"type": "json_object"})
    response = await json_llm.ainvoke(messages)
    
    # Parse and return the response
    return json.loads(response.content)


# Keep the original function for backward compatibility
def grade_question_legacy(schema: str = None):
    return grade_question_prompt(schema)
