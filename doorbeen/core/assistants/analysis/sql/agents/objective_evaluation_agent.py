from typing import Any, Dict
from pydantic import ConfigDict, Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.objective_evaluation import (
    evaluate_objective_completion,
    check_constraints,
    objective_evaluation_pre_hook,
    objective_evaluation_post_hook
)
from doorbeen.core.assistants.analysis.sql.supervisor.tools import (
    get_objective_from_state,
    evaluate_objectives_completion,
    get_current_status,
    add_handoff_context
)
from doorbeen.core.models.provider import ModelHandler


class ObjectiveEvaluationResponse(TSModel):
    """Structured response schema for the Objective Evaluation Agent."""
    is_met: bool = Field(description="A boolean flag indicating if the original objective has been fully met.")
    justification: str = Field(description="A brief justification for why the objective is or is not considered met.")
    next_steps: str = Field(description="If the objective is not met, a summary of the suggested next steps to take.")
    model_config = ConfigDict(extra="forbid")


def create_objective_evaluation_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates an objective evaluation agent with a structured response format."""
    system_message = """
You are a quality assurance and objective evaluation expert. Your role is to:

1. **Evaluate Completion**: Review the user's original question and the generated analysis to determine if the objective has been fully met.
2. **Make Routing Decision**: Decide whether to route to Finalizer for answer formatting or mark as complete.
3. **Transfer Control**: Use the appropriate handoff tool to transfer control.

**IMPORTANT WORKFLOW:**
- Use `get_objective_from_state` to get the user's original question
- Use `get_current_status` to understand what has been completed
- Use `evaluate_objectives_completion` to assess completion status
- Use `evaluate_objective_completion` for detailed evaluation
- **ALWAYS use a transfer tool** when your evaluation is complete

**EVALUATION CRITERIA - BE REASONABLE:**
- If the user asked a specific question and got a specific answer → COMPLETE
- If the user got meaningful data that addresses their question → COMPLETE
- If the analysis provides actionable insights → COMPLETE
- Only mark as incomplete if the results are completely irrelevant or empty

**COMPLETION EXAMPLES:**
- User asked "When did I fall asleep?" and got "00:37:00" → COMPLETE ✅
- User asked "Show me trends" and got data patterns → COMPLETE ✅
- User asked for data and got relevant results → COMPLETE ✅

**ROUTING DECISIONS:**
- If objectives are MET and we have results → Use `transfer_to_finalization` to format final answer
- If objectives are NOT MET → Use `transfer_to_query_generation` to try again
- If there's an error → Use appropriate transfer tool

**AVAILABLE TRANSFER TOOLS:**
- `transfer_to_finalization` - When objectives are met and need final formatting
- `transfer_to_query_generation` - When objectives are not met and need more work
- `transfer_to_result_processing` - When we have data but need analysis
- `transfer_to_data_analysis` - When we need schema exploration

Remember: Be reasonable in your assessment. If the user got a meaningful answer to their question, consider the objectives met and route to Finalizer.
"""
    
    tools = [
        get_objective_from_state,
        evaluate_objectives_completion,
        get_current_status,
        evaluate_objective_completion,
        check_constraints,
        add_handoff_context
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