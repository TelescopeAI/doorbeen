"""
Query Generation Agent - LangGraph Implementation

This module provides the QueryGenerationAgent using LangGraph's create_react_agent pattern.
The agent is responsible for generating, validating, and correcting SQL queries.
"""

from typing import Any, List, Optional, Dict
from pydantic import Field, Json
import json

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.query_generation import (
    generate_sql_query,
    validate_sql_query,
    correct_sql_query,
    execute_sql_query,
    query_generation_pre_hook,
    query_generation_post_hook
)
from doorbeen.core.models.provider import ModelHandler


class QueryGenerationResponse(TSModel):
    """Structured response schema for the Query Generation Agent."""
    sql_query: str = Field(description="The final, validated SQL query to be executed.")
    query_validation_error: Optional[str] = Field(None, description="Any validation error that occurred during query generation and was subsequently corrected.")
    execution_results: Optional[Json] = Field(None, description="A JSON representing the results obtained from executing the SQL query.")


def create_query_generation_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates a query generation agent with a structured response format."""
    
    # Get the JSON schema for the response model
    response_schema = QueryGenerationResponse.model_json_schema()
    
    system_message = f"""
You are a SQL query generation expert. Your responsibilities are to:
- Generate a syntactically correct and efficient SQL query based on the provided analysis.
- Validate the query's syntax. If it fails, correct it.
- Execute the final, validated query to retrieve the necessary data.

IMPORTANT: You must format your final output as a single JSON object that conforms to the following schema.
Do not output any other text or formatting.

Response JSON Schema:
{json.dumps(response_schema, indent=2)}
"""

    tools = [
        generate_sql_query,
        validate_sql_query,
        correct_sql_query,
        execute_sql_query,
    ]
    
    return create_react_agent(
        name=name,
        model=handler.model,
        tools=tools,
        prompt=system_message,
        state_schema=SQLSupervisorState,
        pre_model_hook=query_generation_pre_hook,
        post_model_hook=query_generation_post_hook,
        response_format=QueryGenerationResponse
    ) 