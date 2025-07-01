import json
from typing_extensions import Annotated

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.prebuilt import InjectedState

from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState


@tool
async def get_schema(config: RunnableConfig) -> str:
    """Get the schema of the specified tables."""
    configuration = config.get("configurable", {})
    connection: CommonSQLClient = configuration.get("connection")
    
    if not connection:
        return json.dumps({"success": False, "error": "Database connection not set."})
    
    try:
        schema = connection.get_schema().model_dump_json()
        return json.dumps({"success": True, "schema": schema})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def data_analysis_pre_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Pre-model hook for data analysis agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "DataAnalysis",
        "data": {
            "scope": "DataAnalysis",
            "description": "Exploring dataset tables and schema structure",
            "content": "🔍 Starting database schema exploration and analysis"
        }
    }
    return {"agent_lifecycle_events": [event]}


def data_analysis_post_hook(state: Annotated[SQLSupervisorState, InjectedState]) -> dict:
    """Post-model hook for data analysis agent - emits agent end event"""
    event = {
        "type": "agent:end",
        "name": "DataAnalysis",
        "data": {
            "scope": "DataAnalysis",
            "description": "Finished analyzing schema and identified relevant tables",
            "content": "✅ Completed database schema analysis and exploration"
        }
    }
    return {"agent_lifecycle_events": [event]} 