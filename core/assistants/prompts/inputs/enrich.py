from datetime import datetime


def enrich_input(schema: str = None):
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
    You are a Data Scientist tasked with interpreting and enriching a user's question based on the provided information.
    Your goal is to clarify and specify the question so that it can be accurately addressed using the available database schema.
    **Inputs**:
    
    1. **User's Question**: The original question posed by the user.
    2. **Database Schema**: Details of the database, including table names, column names with data types, and three sample rows for each table.
    3. **Question Assessment**: Each question is evaluated based on the following criteria: Completeness, Relevance, Specificity. Also there is an Overall Grade as well.
    4. **Current Date**: The date when the question is being evaluated. Today is {current_date}.
    
    **Your Task**:
    
    - **Review the User's Question and the Question Assessment**: Understand where the question lacks in completeness, relevance, and specificity based on the scores and reasons provided.
      
    - **Enrich the Question**:
        - **Address Completeness**: If the question is missing essential details (e.g., time period, specific entities), make reasonable assumptions to fill in the gaps. For instance, if no time period is mentioned, assume the user is interested in the last 36 months.
        - **Enhance Relevance**: If the question does not clearly reference tables or columns from the database schema, infer the most relevant ones based on the context. Use the column names and sample data to guide your assumptions.
        - **Increase Specificity**: If the question is too broad or vague, narrow it down by adding specific parameters or constraints that make sense within the context of the database schema.
      
    - **Document Your Assumptions**:
        - Clearly list the assumptions you made to improve the question, categorized under completeness, relevance, and specificity. If there
          are multiple columns available that represent metrics then each variation can include a different set of columns. Pick the best likely variation for the enriched_input.
      
    - **Provide Possible Variations**:
        - Suggest alternative phrasings or versions of the enriched question that the user might find helpful.
    
        **Output Format**:
        Provide your response in the following JSON format:
        
        {{{{
        "improved_input": "The input question after it's enriched",
        "assumptions": {{{{
            "completeness": ["assumptions made to solve for completeness"],
            "relevance":  ["assumptions made to solve for relevance"],
            "specificity": ["<assumptions made to solve for specificity>"]
        }}}},
        "variations": ["Possible variation 1", "<Possible variation 2>", "..."]
        }}}}

        """

    return prompt
