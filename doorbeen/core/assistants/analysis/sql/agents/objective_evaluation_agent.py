from typing import Any, Dict
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.objective_evaluation import (
    evaluate_objective_completion,
    check_constraints,
    objective_evaluation_pre_hook,
    objective_evaluation_post_hook
)
from doorbeen.core.models.provider import ModelHandler


class ObjectiveEvaluationResponse(TSModel):
    """Structured response schema for the Objective Evaluation Agent."""
    is_met: bool = Field(description="A boolean flag indicating if the original objective has been fully met.")
    justification: str = Field(description="A brief justification for why the objective is or is not considered met.")
    next_steps: str = Field(description="If the objective is not met, a summary of the suggested next steps to take.")


def create_objective_evaluation_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates an objective evaluation agent with a structured response format."""
    system_message = """
You are a quality assurance and objective evaluation expert. Your role is to:
- Review the user's original question and the generated analysis.
- Evaluate if the analysis fully and accurately answers the question.
- Check if all constraints from the user's prompt have been met.
- Your final output will be automatically structured to reflect your evaluation.
"""
    tools = [
        evaluate_objective_completion,
        check_constraints,
    ]
    
    return create_react_agent(
        name=name,
        model=handler.model,
        tools=tools,
        prompt=system_message,
        state_schema=SQLSupervisorState,
        pre_model_hook=objective_evaluation_pre_hook,
        post_model_hook=objective_evaluation_post_hook,
        response_format=ObjectiveEvaluationResponse
    ) 