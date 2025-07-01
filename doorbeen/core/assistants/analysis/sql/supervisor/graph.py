from typing import Any, Dict, List, Optional
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState

# Import agent creation functions to avoid code duplication
from doorbeen.core.assistants.analysis.sql.agents.data_analysis_agent import create_data_analysis_agent
from doorbeen.core.assistants.analysis.sql.agents.query_generation_agent import create_query_generation_agent
from doorbeen.core.assistants.analysis.sql.agents.result_processing_agent import create_result_processing_agent
from doorbeen.core.assistants.analysis.sql.agents.objective_evaluation_agent import create_objective_evaluation_agent
from doorbeen.core.assistants.analysis.sql.agents.finalization_agent import create_finalization_agent
from doorbeen.core.assistants.analysis.sql.supervisor.handoff_tools import add_handoff_tools_to_agent
from doorbeen.core.assistants.analysis.sql.supervisor.tools import (
        get_objective_from_state,
        get_schema_context,
        update_schema_context,
        get_sql_query,
        update_sql_query,
        get_execution_results,
        update_execution_results,
        get_analysis_summary,
        update_analysis_summary,
        evaluate_objectives_completion,
        update_final_answer,
        set_error,
        add_handoff_context,
        get_current_status,
        get_handoff_context
    )
    


def create_sql_supervisor_graph(
    handler: ModelHandler,
    connection: CommonSQLClient,
    question: str,
    agent_config: Optional[Dict[str, Any]] = None,
    checkpointer: Optional[Any] = None
):
    """Create and return the supervisor agent graph using LangGraph's create_supervisor."""

    # Create specialized agents using dedicated creation functions
    data_analysis_agent = create_data_analysis_agent(
        name="DataAnalyst",
        handler=handler
    )
    add_handoff_tools_to_agent(data_analysis_agent)
    
    query_generation_agent = create_query_generation_agent(
        name="QueryGenerator", 
        handler=handler
    )
    add_handoff_tools_to_agent(query_generation_agent)
    
    result_processing_agent = create_result_processing_agent(
        name="ResultProcessor",
        handler=handler
    )
    add_handoff_tools_to_agent(result_processing_agent)
    
    objective_evaluation_agent = create_objective_evaluation_agent(
        name="ObjectiveEvaluator",
        handler=handler
    )
    add_handoff_tools_to_agent(objective_evaluation_agent)
    
    finalization_agent = create_finalization_agent(
        name="Finalizer",
        handler=handler
    )
    add_handoff_tools_to_agent(finalization_agent)

    # Define supervisor instructions with objective-driven intelligence
    supervisor_prompt = f"""
You are an intelligent SQL Analysis Supervisor coordinating specialized agents to answer: "{question}"

AGENTS AVAILABLE:
- DataAnalyst: Schema exploration, data understanding, domain detection
- QueryGenerator: SQL creation, validation, optimization, execution  
- ResultProcessor: Data analysis, statistical insights, trend identification
- ObjectiveEvaluator: Completion assessment, quality validation
- Finalizer: Answer formatting, suggestions, follow-ups

INTELLIGENT ROUTING PRINCIPLES:
1. Analyze the question complexity and data requirements
2. Start with DataAnalyst ONLY if schema understanding is needed
3. Route to QueryGenerator when ready to create/execute SQL
4. Use ResultProcessor when you have data to analyze
5. Call ObjectiveEvaluator to check if user's question is fully answered
6. Use Finalizer only when all objectives are complete

CRITICAL GUIDELINES:
- Don't force a linear sequence - skip agents if their expertise isn't needed
- Route based on current context and remaining objectives
- Continue until the user's question is FULLY answered
- Each agent should build on previous agents' work
- Agents have free will in which tools to use - you only coordinate handoffs
- Be efficient: don't repeat work that's already been done well
- If simple questions can be answered quickly, do so - don't over-engineer

OBJECTIVE TRACKING:
- Continuously assess what parts of the user's question remain unanswered
- Route to the most appropriate agent based on what's missing
- Only finish when you're confident the user's question is comprehensively addressed

Goal: Efficiently provide a complete, accurate answer to the user's question.
"""
    supervisor_tools = [
        get_objective_from_state,
        get_schema_context,
        update_schema_context,
        get_sql_query,
        update_sql_query,
        get_execution_results,
        update_execution_results,
        get_analysis_summary,
        update_analysis_summary,
        evaluate_objectives_completion,
        update_final_answer,
        set_error,
        add_handoff_context,
        get_current_status,
        get_handoff_context
    ]


    # Create the supervisor using LangGraph's built-in function
    supervisor_graph = create_supervisor(
        agents=[
            data_analysis_agent,
            query_generation_agent,
            result_processing_agent,
            objective_evaluation_agent,
            finalization_agent
        ],
        tools=supervisor_tools,
        model=handler.model,
        prompt=supervisor_prompt,
        state_schema=SQLSupervisorState,
        supervisor_name="supervisor",
        # Ensure agent names are properly included in messages
        include_agent_name="inline"
    )

    # Compile the graph to get a CompiledStateGraph
    # Pass checkpointer during compilation if provided
    compiled_graph = supervisor_graph.compile(checkpointer=checkpointer)
    
    return compiled_graph 