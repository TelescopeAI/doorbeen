"""
Supervisor-compatible tools for SQL analysis agents.

These tools are designed to work with SQLSupervisorState and can be injected
into agents using InjectedState pattern.
"""

from typing import Annotated, Dict, Any, List
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState



@tool
def get_objective_from_state(
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Get the user's original question/objective from state."""
    return state.input or "No objective specified"


@tool
def get_schema_context(
    state: Annotated[SQLSupervisorState, InjectedState]
) -> Dict[str, Any]:
    """Get database schema context from state."""
    return state.schema_context or {}


@tool
def update_schema_context(
    schema_info: Dict[str, Any],
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Update schema context in state."""
    if state.schema_context is None:
        state.schema_context = {}
    state.schema_context.update(schema_info)
    return "Schema context updated successfully"


@tool
def get_sql_query(
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Get the current SQL query from state."""
    return state.sql_query or "No SQL query generated yet"


@tool
def update_sql_query(
    query: str,
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Update the SQL query in state."""
    state.sql_query = query
    return "SQL query updated successfully"


@tool
def get_execution_results(
    state: Annotated[SQLSupervisorState, InjectedState]
) -> List[Dict[str, Any]]:
    """Get query execution results from state."""
    return state.execution_results or []


@tool
def update_execution_results(
    results: List[Dict[str, Any]],
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Update execution results in state."""
    state.execution_results = results
    return "Execution results updated successfully"


@tool
def get_analysis_summary(
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Get analysis summary from state."""
    return state.analysis_summary or "No analysis completed yet"


@tool
def update_analysis_summary(
    summary: str,
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Update analysis summary in state."""
    state.analysis_summary = summary
    return "Analysis summary updated successfully"


@tool
def evaluate_objectives_completion(
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """
    Evaluate whether the user's objectives have been met.
    
    Returns status indicating completion level.
    """
    objective = state.input
    has_query = bool(state.sql_query)
    has_results = bool(state.execution_results)
    has_analysis = bool(state.analysis_summary)
    
    if not objective:
        return "No clear objective to evaluate"
    
    if not has_query:
        state.objectives_met = "needs_query_generation"
        return "Needs SQL query generation to proceed"
    
    if not has_results:
        state.objectives_met = "needs_execution"
        return "SQL query exists but needs execution"
    
    if not has_analysis:
        state.objectives_met = "needs_analysis" 
        return "Results exist but need analysis to answer user's question"
    
    # Check if we have a comprehensive answer
    if state.final_answer:
        state.objectives_met = "all_objectives_met"
        return "All objectives completed - user question fully answered"
    
    state.objectives_met = "needs_finalization"
    return "Analysis complete but needs final answer formatting"


@tool
def update_final_answer(
    answer: str,
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Update the final answer in state."""
    state.final_answer = answer
    state.mark_complete()
    return "Final answer updated and marked complete"


@tool
def set_error(
    error_message: str,
    state: Annotated[SQLSupervisorState, InjectedState],
    error_type: str = "general"
) -> str:
    """Set error information in state."""
    state.error = {
        "type": error_type,
        "message": error_message
    }
    return f"Error logged: {error_message}"


@tool
def get_current_status(
    state: Annotated[SQLSupervisorState, InjectedState]
) -> Dict[str, Any]:
    """Get current status summary of the analysis."""
    return state.get_status_summary()


@tool
def add_handoff_context(
    context_key: str,
    context_value: Any,
    state: Annotated[SQLSupervisorState, InjectedState]
) -> str:
    """Add context for agent handoffs."""
    state.set_handoff_context({context_key: context_value})
    return f"Handoff context updated: {context_key}"


@tool
def get_handoff_context(
    context_key: str,
    state: Annotated[SQLSupervisorState, InjectedState]
) -> Any:
    """Get handoff context value."""
    return state.get_handoff_context(context_key)


# Tools grouped by agent type for easy assignment
DATA_ANALYSIS_TOOLS = [
    get_objective_from_state,
    get_schema_context,
    update_schema_context,
    add_handoff_context,
    get_current_status
]

QUERY_GENERATION_TOOLS = [
    get_objective_from_state,
    get_schema_context,
    get_sql_query,
    update_sql_query,
    update_execution_results,
    set_error,
    add_handoff_context,
    get_current_status
]

RESULT_PROCESSING_TOOLS = [
    get_objective_from_state,
    get_execution_results,
    get_analysis_summary,
    update_analysis_summary,
    add_handoff_context,
    get_current_status
]

OBJECTIVE_EVALUATION_TOOLS = [
    get_objective_from_state,
    evaluate_objectives_completion,
    get_current_status,
    add_handoff_context
]

FINALIZATION_TOOLS = [
    get_objective_from_state,
    get_analysis_summary,
    get_execution_results,
    update_final_answer,
    get_current_status
] 