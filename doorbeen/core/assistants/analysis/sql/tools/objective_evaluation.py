import json
from typing import Dict, Any, List
from typing_extensions import Annotated

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.prebuilt import InjectedState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState


@tool
async def evaluate_objective_completion(
    summary: str, 
    state: Annotated[SQLAssistantState, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"]
) -> str:
    """Evaluate if the original objective has been met."""
    # Automatically get objective from state.input instead of requiring LLM to provide it
    objective = state.input
    
    # Get handler from config (still need RunnableConfig for external resources)
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Given the user's objective and the summary of the findings, determine if the objective has been fully met.

Objective: {objective}
Summary: {summary}

Respond with "true" if the objective is met, and "false" otherwise, followed by a brief justification.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "result": response.content})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def suggest_next_steps(
    summary: str, 
    state: Annotated[SQLAssistantState, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"]
) -> str:
    """If the objective is not met, suggest the next steps."""
    # Automatically get objective from state.input
    objective = state.input
    
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
The user's objective has not yet been fully met. Based on the objective and the summary of findings so far, what are the next logical steps to take?

Objective: {objective}
Summary: {summary}

Suggest a list of concrete next steps.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "next_steps": response.content.split('\n')})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# Keep existing functions for backward compatibility
@tool
async def check_completeness(
    analysis: str, 
    state: Annotated[SQLSupervisorState, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"]
) -> str:
    """Evaluate if the analysis completely answers the original question."""
    # Automatically get question from state.input
    question = state.input
    
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Original question: {question}
Analysis: {analysis}

Does this analysis completely answer the original question? Answer yes or no and provide reasoning.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        completeness = "yes" in response.content.lower()
        return json.dumps({"success": True, "is_complete": completeness, "explanation": response.content})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def check_constraints(
    analysis: str, 
    state: Annotated[SQLSupervisorState, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"]
) -> str:
    """Check if any constraints mentioned in the original question have been addressed in the analysis."""
    # Automatically get question from state.input
    question = state.input
    
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Original question: {question}
Analysis: {analysis}

Are there any constraints or specific requirements in the question that have been addressed in the analysis?
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "constraints_check": response.content})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def objective_evaluation_pre_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Pre-model hook for objective evaluation agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "ObjectiveEvaluation",
        "data": {
            "scope": "ObjectiveEvaluation",
            "description": "Evaluating if analysis meets the original objective",
            "content": "🎯 Starting objective evaluation and completeness check"
        }
    }
    return {"agent_lifecycle_events": [event]}


def objective_evaluation_post_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Post-model hook for objective evaluation agent - emits agent end event"""
    event = {
        "type": "agent:end",
        "name": "ObjectiveEvaluation",
        "data": {
            "scope": "ObjectiveEvaluation",
            "description": "Assessed objective completion and identified next steps",
            "content": "✅ Completed objective evaluation and assessment"
        }
    }
    return {"agent_lifecycle_events": [event]} 