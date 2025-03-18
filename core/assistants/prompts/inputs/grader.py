from langchain_core.prompts import ChatPromptTemplate


def grade_question(schema: str = None):
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
            - **Score**: Assign a score from **1 (highly relevant)** to **10 (not relevant)**.

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

        - Set the flag `"should_enrich"` to **true** if the question needs to be clarified or specified further.
        - Set it to **false** if the question is good to proceed as is.
        - Only if the overall grade is above **4**, the question should be enriched.

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
