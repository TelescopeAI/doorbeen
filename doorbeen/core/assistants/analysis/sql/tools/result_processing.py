import json
from typing import Dict, Any, List
from typing_extensions import Annotated

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.prebuilt import InjectedState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState


@tool
async def summarize_data(config: Annotated[RunnableConfig, "Configuration"], data: List[Dict[str, Any]]) -> str:
    """Summarize the provided data."""
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Please summarize the following data:
{json.dumps(data, indent=2)}

Provide a concise summary.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "summary": response.content})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def identify_trends(config: Annotated[RunnableConfig, "Configuration"], data: List[Dict[str, Any]]) -> str:
    """Identify trends in the provided data."""
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Analyze the following data and identify any notable trends or patterns:
{json.dumps(data, indent=2)}

List the trends you find.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "trends": response.content.split('\n')})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def extract_key_insights(
    data: List[Dict[str, Any]], 
    state: Annotated[SQLSupervisorState, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"]
) -> str:
    """Extract key insights from the data relevant to the objective."""
    # Automatically get objective from state.input
    objective = state.input
    
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Given the user's objective and the following data, extract the key insights.

Objective: {objective}
Data:
{json.dumps(data, indent=2)}

Provide a list of key insights.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "insights": response.content.split('\n')})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def result_processing_pre_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Pre-model hook for result processing agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "ResultProcessing",
        "data": {
            "scope": "ResultProcessing",
            "description": "Processing query results and extracting insights",
            "content": "📊 Starting result processing and analysis"
        }
    }
    return {"agent_lifecycle_events": [event]}


def result_processing_post_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Post-model hook for result processing agent - emits agent end event"""
    event = {
        "type": "agent:end",
        "name": "ResultProcessing",
        "data": {
            "scope": "ResultProcessing",
            "description": "Extracted key insights and patterns from results",
            "content": "✅ Completed result processing and insight extraction"
        }
    }
    return {"agent_lifecycle_events": [event]} 