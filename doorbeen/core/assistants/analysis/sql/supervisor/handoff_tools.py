"""
Handoff tools for LangGraph supervisor pattern

This module provides handoff tools that allow agents to transfer control to other agents
in the multi-agent system using LangGraph's supervisor pattern.
"""

from langgraph_supervisor import create_handoff_tool
from typing import Callable

# Create handoff tools for each agent
transfer_to_data_analysis = create_handoff_tool(
    agent_name="data_analysis_agent",
    description="Transfer to data analysis agent for schema exploration and data understanding"
)

transfer_to_query_generation = create_handoff_tool(
    agent_name="query_generation_agent",
    description="Transfer to query generation agent for SQL creation and optimization"
)

transfer_to_result_processing = create_handoff_tool(
    agent_name="result_processing_agent", 
    description="Transfer to result processing agent for data analysis and insight extraction"
)

transfer_to_objective_evaluation = create_handoff_tool(
    agent_name="objective_evaluation_agent",
    description="Transfer to objective evaluation agent for completion assessment"
)

transfer_to_finalization = create_handoff_tool(
    agent_name="finalization_agent",
    description="Transfer to finalization agent for answer formatting and presentation"
)

# --- PATCH: Wrap handoff tools to always receive a dict for state ---
def _wrap_handoff_tool(tool: Callable) -> Callable:
    async def wrapped(*args, **kwargs):
        # Find the state argument (first positional or 'state' kwarg)
        if args:
            state = args[0]
            rest = args[1:]
        else:
            state = kwargs.get("state")
            rest = ()
        # Convert state to dict if it's a Pydantic model
        if hasattr(state, "dict"):
            state = state.dict()
        # Rebuild args/kwargs with dict state
        if args:
            args = (state,) + rest
        else:
            kwargs["state"] = state
        return await tool(*args, **kwargs)
    return wrapped

transfer_to_data_analysis = _wrap_handoff_tool(transfer_to_data_analysis)
transfer_to_query_generation = _wrap_handoff_tool(transfer_to_query_generation)
transfer_to_result_processing = _wrap_handoff_tool(transfer_to_result_processing)
transfer_to_objective_evaluation = _wrap_handoff_tool(transfer_to_objective_evaluation)
transfer_to_finalization = _wrap_handoff_tool(transfer_to_finalization)

# List of all handoff tools
ALL_HANDOFF_TOOLS = [
    transfer_to_data_analysis,
    transfer_to_query_generation,
    transfer_to_result_processing,
    transfer_to_objective_evaluation,
    transfer_to_finalization
]

def add_handoff_tools_to_agent(agent, handoff_tools=None):
    """Add handoff tools to an agent"""
    if handoff_tools is None:
        handoff_tools = ALL_HANDOFF_TOOLS
    
    # Add handoff tools to agent's tools list
    if hasattr(agent, 'tools'):
        agent.tools.extend(handoff_tools)
    else:
        # If agent doesn't have tools attribute, create it
        agent.tools = handoff_tools
    
    return agent 