from typing import Any, List, Dict
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.result_processing import (
    summarize_data,
    identify_trends,
    extract_key_insights,
    result_processing_pre_hook,
    result_processing_post_hook
)
from doorbeen.core.models.provider import ModelHandler


class ResultProcessingResponse(TSModel):
    """Structured response schema for the Result Processing Agent."""
    data_summary: str = Field(description="A concise summary of the key information found in the raw SQL query results.")
    trends_and_patterns: List[str] = Field(description="A list of notable trends, patterns, or anomalies identified in the data.")
    key_insights: List[str] = Field(description="A list of key, actionable insights extracted from the data that are relevant to the user's objective.")


def create_result_processing_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates a result processing agent with a structured response format."""
    system_message = """
You are a data analysis and insights expert. Your responsibilities include:
- Analyzing the raw data returned from a SQL query.
- Summarizing the data, identifying trends, and extracting key insights that directly address the user's original question.
- Your final output will be automatically structured to contain the summary, trends, and insights.
"""
    tools = [
        summarize_data,
        identify_trends,
        extract_key_insights,
    ]
    
    return create_react_agent(
        name=name,
        model=handler.model,
        tools=tools,
        prompt=system_message,
        state_schema=SQLSupervisorState,
        pre_model_hook=result_processing_pre_hook,
        post_model_hook=result_processing_post_hook,
        response_format=ResultProcessingResponse
    ) 