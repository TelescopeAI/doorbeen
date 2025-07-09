from typing import Any, List
from pydantic import ConfigDict, Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.finalization import (
    format_final_answer,
    generate_follow_up_questions,
    finalization_pre_hook,
    finalization_post_hook
)
from doorbeen.core.models.provider import ModelHandler


class FinalizationResponse(TSModel):
    """Structured response schema for the Finalization Agent."""
    final_summary: str = Field(description="A final, comprehensive summary that directly addresses the user's objective, intended for a non-technical audience.")
    visualization_suggestions: List[str] = Field(description="A list of suggested visualizations to help illustrate the findings.", default_factory=list)
    follow_up_questions: List[str] = Field(description="A list of relevant follow-up questions a user might ask based on the analysis.", default_factory=list)
    final_answer: str = Field(description="The final, formatted answer ready to be presented to the user.")
    
    model_config = ConfigDict(extra="forbid")


def create_finalization_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates a finalization agent with a structured response format."""
    system_message = """
You are the finalization and presentation expert. Your responsibilities are:
- Take the completed analysis and format it into a clear, concise, and user-friendly final answer.
- Generate relevant follow-up questions that the user might have.
- Ensure the final output is well-structured and easy to understand.
- Your output will be structured automatically based on your work.
"""
    tools = [
        format_final_answer,
        generate_follow_up_questions,
    ]
    
    return create_react_agent(
        name=name,
        model=handler.model,
        tools=tools,
        prompt=system_message,
        state_schema=SQLSupervisorState,
        pre_model_hook=finalization_pre_hook,
        post_model_hook=finalization_post_hook,
        response_format=FinalizationResponse
    ) 