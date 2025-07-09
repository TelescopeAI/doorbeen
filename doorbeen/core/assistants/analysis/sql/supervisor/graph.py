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
from doorbeen.core.assistants.analysis.sql.agents.finalization_agent import create_finalization_agent
# Handoff tools are automatically created by create_supervisor
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
        get_handoff_context,
        check_query_execution_status,
        classify_question_type,
        answer_general_knowledge_question
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
    # Note: create_supervisor automatically generates transfer tools based on agent names
    data_analysis_agent = create_data_analysis_agent(
        name="DataAnalyst",
        handler=handler
    )
    
    query_generation_agent = create_query_generation_agent(
        name="QueryGenerator", 
        handler=handler
    )
    
    result_processing_agent = create_result_processing_agent(
        name="ResultProcessor",
        handler=handler
    )

    finalization_agent = create_finalization_agent(
        name="Finalizer",
        handler=handler
    )

    # Define supervisor instructions with intelligent question classification
    supervisor_prompt = f"""
You are an intelligent SQL Analysis Supervisor coordinating specialized agents to answer: "{question}"

**CRITICAL WORKFLOW RULES:**

**STEP 1 - QUESTION CLASSIFICATION (MANDATORY FIRST STEP):**
- ALWAYS start by using `classify_question_type` tool to determine if the question requires data analysis
- This prevents unnecessary agent calls for general knowledge questions

**STEP 2 - ROUTING DECISION:**
- **General Knowledge Questions**: Use `answer_general_knowledge_question` then provide the actual answer using your knowledge
- **Data Analysis Questions**: Use the ONE-WAY agent workflow below

**ONE-WAY AGENT WORKFLOW (NEVER GO BACKWARDS):**
1. **DataAnalyst**: Schema exploration, query planning, sample data collection (ONCE ONLY)
2. **QueryGenerator**: Draft-validate-execute workflow with zero-result intelligence (ONCE ONLY)
3. **ResultProcessor**: Comprehensive data analysis and insight extraction (ONCE ONLY)
4. **Finalizer**: Answer formatting (ONCE ONLY)

**CRITICAL ROUTING RULES:**
- **NEVER** route back to DataAnalyst once schema is available
- **NEVER** route back to DataAnalyst after QueryGenerator has run
- **NEVER** route back to DataAnalyst after query execution
- **ALWAYS** use `check_query_execution_status` to see current progress before routing
- **ALWAYS** move forward in the workflow: DataAnalyst → QueryGenerator → ResultProcessor → Finalizer

**ROUTING DECISION LOGIC:**
1. No schema context → `transfer_to_DataAnalyst` (FIRST TIME ONLY)
2. Schema exists but no query/results → `transfer_to_QueryGenerator` (FIRST TIME ONLY)
3. Query and results exist but no analysis → `transfer_to_ResultProcessor` (FIRST TIME ONLY)
4. Analysis complete but no final answer → `transfer_to_Finalizer` (FIRST TIME ONLY)
5. Final answer exists → COMPLETE

**TOOLS AVAILABLE:**
- `classify_question_type`: Classify if question needs data analysis
- `answer_general_knowledge_question`: Mark as general knowledge and prepare for direct answer
- `check_query_execution_status`: Check workflow progress and get detailed status
- Agent transfer tools: `transfer_to_DataAnalyst`, `transfer_to_QueryGenerator`, `transfer_to_ResultProcessor`, `transfer_to_Finalizer`

**WORKFLOW MONITORING:**
- ALWAYS use `check_query_execution_status` before making routing decisions
- This tool shows you the actual SQL query executed and results obtained
- It provides clear routing guidance based on current workflow state

**IMPORTANT NOTES:**
- Each agent should only be called ONCE in the workflow
- The workflow is ONE-WAY: DataAnalyst → QueryGenerator → Finalizer
- Never go backwards in the workflow unless you think you are missing something that is required for the workflow to complete
- Always check status before routing to see what has been completed

**EXAMPLE WORKFLOW:**
1. Use `classify_question_type` → data analysis required
2. Use `check_query_execution_status` → no schema
3. Use `transfer_to_DataAnalyst` → schema obtained
4. Use `check_query_execution_status` → schema available, no query
5. Use `transfer_to_QueryGenerator` → query executed, results obtained
6. Use `check_query_execution_status` → results available, no analysis
7. Use `transfer_to_ResultProcessor` → comprehensive analysis completed
8. Use `check_query_execution_status` → analysis complete, no final answer
9. Use `transfer_to_Finalizer` → final answer generated
10. COMPLETE

Goal: Provide accurate answers efficiently using the ONE-WAY workflow without backtracking.
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
        get_handoff_context,
        check_query_execution_status,
        classify_question_type,
        answer_general_knowledge_question
    ]


    # Create the supervisor using LangGraph's built-in function
    supervisor_graph = create_supervisor(
        agents=[
            data_analysis_agent,
            query_generation_agent,
            result_processing_agent,
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