import json
import logging
from typing import Dict, Any, List, Optional
from typing_extensions import Annotated

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.prebuilt import InjectedState

from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState


@tool
async def generate_sql_query(config: Annotated[RunnableConfig, "Configuration"], analysis: str) -> str:
    """Generate a SQL query based on the analysis."""
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
Based on the following analysis, generate a SQL query.

Analysis:
{analysis}

Return only the SQL query.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "query": response.content})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def validate_sql_query(config: Annotated[RunnableConfig, "Configuration"], query: str) -> str:
    """Validate the syntax of a SQL query."""
    configuration = config.get("configurable", {})
    connection: CommonSQLClient = configuration.get("connection")
    
    if not connection:
        return json.dumps({"success": False, "error": "Database connection not set."})

    try:
        is_valid = await connection.validate_query(query)
        return json.dumps({"success": True, "is_valid": is_valid})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def correct_sql_query(config: Annotated[RunnableConfig, "Configuration"], query: str, error_message: str) -> str:
    """Correct a SQL query that has a syntax error."""
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not set."})

    prompt = f"""
The following SQL query has an error:
{query}

Error: {error_message}

Please correct the query. Return only the corrected SQL query.
"""
    try:
        response = await handler.model.ainvoke(prompt)
        return json.dumps({"success": True, "corrected_query": response.content})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def execute_sql_query(config: Annotated[RunnableConfig, "Configuration"], query: str) -> str:
    """Execute a SQL query and return the results."""
    configuration = config.get("configurable", {})
    connection: CommonSQLClient = configuration.get("connection")
    
    if not connection:
        return json.dumps({"success": False, "error": "Database connection not set."})
    try:
        result = await connection.query(query)
        return json.dumps({"success": True, "result": result})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def query_generation_pre_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Pre-model hook for query generation agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "QueryGeneration",
        "data": {
            "scope": "QueryGeneration",
            "description": "Generating SQL query from analysis results",
            "content": "⚡ Starting SQL query generation based on analysis"
        }
    }
    return {"agent_lifecycle_events": [event]}


def query_generation_post_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Post-model hook for query generation agent - emits agent end event"""
    event = {
        "type": "agent:end",
        "name": "QueryGeneration",
        "data": {
            "scope": "QueryGeneration", 
            "description": "Generated and validated SQL query successfully",
            "content": "✅ Completed SQL query generation and validation"
        }
    }
    return {"agent_lifecycle_events": [event]} 