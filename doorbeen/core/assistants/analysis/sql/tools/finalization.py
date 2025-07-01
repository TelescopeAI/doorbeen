import json
from typing import List, Dict, Any
from typing_extensions import Annotated

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.prebuilt import InjectedState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState


@tool
async def create_final_summary(
    insights: List[str], 
    state: Annotated[SQLSupervisorState, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"]
) -> str:
    """Create a final, user-facing summary of the analysis."""
    # Automatically get objective from state.input
    objective = state.input
    
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    insights_str = "\n- ".join(insights)
    prompt = f"""
Based on the following insights, create a final, comprehensive summary that directly addresses the user's objective.

Objective: {objective}
Key Insights:
- {insights_str}

The summary should be clear, concise, and easy for a non-technical user to understand.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "summary": response.content})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def generate_visualizations(config: Annotated[RunnableConfig, "Configuration"], data: List[Dict[str, Any]], objective: str) -> str:
    """Suggest visualizations to help illustrate the findings."""
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Given the data and the user's objective, what visualizations (e.g., bar chart, line graph, pie chart) would be most effective for illustrating the key findings?

Objective: {objective}
Data Columns: {list(data[0].keys()) if data else []}

Suggest a list of visualizations and what data they should represent.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "visualizations": response.content.split('\n')})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def format_final_answer(
    config: Annotated[RunnableConfig, "Configuration"],
    analysis_summary: str,
    insights: List[str]
) -> str:
    """Format the final answer for the user in a clear and concise way."""
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Format the following analysis into a user-friendly final answer.

Analysis Summary: {analysis_summary}
Key Insights: {', '.join(insights)}

Present the information clearly in markdown format.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "formatted_answer": response.content})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def generate_follow_up_questions(
    config: Annotated[RunnableConfig, "Configuration"],
    analysis_summary: str,
    insights: List[str]
) -> str:
    """Generate relevant follow-up questions based on the analysis."""
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Based on the following analysis, generate 3-5 relevant follow-up questions a user might ask.

Analysis Summary: {analysis_summary}
Key Insights: {', '.join(insights)}

List the questions.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "follow_up_questions": response.content.split('\n')})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def finalization_pre_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Pre-model hook for finalization agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "Finalization",
        "data": {
            "scope": "Finalization",
            "description": "Creating comprehensive final summary and formatting results",
            "content": "📝 Starting final summary and report generation"
        }
    }
    return {"agent_lifecycle_events": [event]}


def finalization_post_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Post-model hook for finalization agent - emits agent end event"""
    event = {
        "type": "agent:end",
        "name": "Finalization",
        "data": {
            "scope": "Finalization",
            "description": "Generated final summary and formatted results for user",
            "content": "✅ Completed final report generation and analysis"
        }
    }
    return {"agent_lifecycle_events": [event]} 