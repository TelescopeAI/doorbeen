from typing import Any, List
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.data_analysis import (
    get_schema,
    data_analysis_pre_hook,
    data_analysis_post_hook
)
from doorbeen.core.models.provider import ModelHandler


class DataAnalysisResponse(TSModel):
    """Structured response schema for the Data Analysis Agent."""
    schema_summary: str = Field(description="A detailed summary of the database schema analysis, highlighting key tables, columns, and relationships.")
    relevant_tables: List[str] = Field(description="A list of table names identified as being most relevant to the user's objective.")


def create_data_analysis_agent(
    name: str,
    handler: ModelHandler,
):
    """
    Creates a data analysis agent with a structured response format.
    """
    system_message = """
You are a database analysis and exploration expert. Your primary responsibility is to analyze the database schema to understand its structure.

- Use your tools to explore the database tables, columns, and relationships.
- Based on the user's objective, identify the most relevant tables.
- Your final output will be structured automatically based on your findings.
"""
    
    tools = [
        get_schema
    ]
    
    return create_react_agent(
        name=name,
        model=handler.model,
        tools=tools,
        prompt=system_message,
        state_schema=SQLSupervisorState,
        pre_model_hook=data_analysis_pre_hook,
        post_model_hook=data_analysis_post_hook,
        response_format=DataAnalysisResponse
    )


# Removed redundant DataAnalysisAgent class - using LangGraph create_data_analysis_agent function instead 