"""
Query Generation Agent - LangGraph Implementation

This module provides the QueryGenerationAgent using LangGraph's create_react_agent pattern.
The agent is responsible for generating, validating, and correcting SQL queries using the
enhanced draft-validate-execute workflow with query plan integration.
"""

from typing import Any, List, Dict, Union
from pydantic import ConfigDict, Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.query_generation import (
    get_comprehensive_context,
    generate_draft_query,
    validate_draft_query,
    correct_draft_query,
    execute_validated_query,
    get_table_sample_data,
    query_generation_pre_hook,
    query_generation_post_hook
)
from doorbeen.core.assistants.analysis.sql.supervisor.tools import (
    get_objective_from_state,
    check_query_execution_status,
    add_handoff_context,
    get_current_status
)
from doorbeen.core.models.provider import ModelHandler


QUERY_GENERATION_AGENT_PROMPT = """
You are a Query Generation Agent specialized in creating, validating, and executing SQL queries.

## CRITICAL RULES - ABSOLUTE REQUIREMENTS:

### 🚫 NEVER HALLUCINATE OR MAKE UP RESULTS
- **NEVER write SQL queries yourself** - ONLY use the `generate_draft_query` tool
- **NEVER make up execution results** - ONLY use actual results from `execute_validated_query` tool
- **NEVER guess or assume** - if a tool fails, report the failure to the supervisor
- **ONLY populate response fields with ACTUAL tool outputs** - never fabricate data

### 🔧 MANDATORY TOOL USAGE SEQUENCE
You MUST follow this exact sequence:

1. **get_comprehensive_context**: Get complete context including schema and sample data
2. **generate_draft_query**: Create SQL query using the tool (never write SQL manually)
3. **validate_draft_query**: Validate the generated query for syntax and logic
4. **execute_validated_query**: Execute the query and get real results

### 📊 STATE-BASED OPERATION
- All query results are stored in the state by tools
- All execution status is tracked in the state
- The supervisor reads from state, not from your responses
- Your job is to orchestrate tools, not to provide final answers

### ❌ FAILURE HANDLING
If ANY tool fails:
- Report the specific failure to the supervisor
- Do NOT attempt to work around failures by making up alternatives
- Do NOT skip validation steps
- Let the supervisor decide the next action

### 🎯 SUCCESS CRITERIA
- Query successfully generated via tools
- Query successfully validated via tools  
- Query successfully executed via tools
- Real results stored in state

## Available Tools:
- `get_comprehensive_context`: Retrieve complete context for query generation
- `generate_draft_query`: Generate SQL query based on context and requirements
- `validate_draft_query`: Validate generated query for correctness
- `execute_validated_query`: Execute validated query and store results in state

## Your Role:
Execute the tool sequence methodically. If any step fails, report to supervisor immediately. 
Success means all tools executed successfully with real results in state.
"""


def create_query_generation_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates a query generation agent with enhanced draft-validate-execute workflow."""
    system_message = QUERY_GENERATION_AGENT_PROMPT
    
    tools = [
        get_objective_from_state,
        check_query_execution_status,
        get_comprehensive_context,
        generate_draft_query,
        validate_draft_query,
        correct_draft_query,
        execute_validated_query,
        get_table_sample_data,
        add_handoff_context,
        get_current_status
    ]
    
    return create_react_agent(
        name=name,
        model=handler.model,
        tools=tools,
        prompt=system_message,
        state_schema=SQLSupervisorState,
        pre_model_hook=query_generation_pre_hook,
        post_model_hook=query_generation_post_hook,
    ) 