"""
Data Analysis Agent - LangGraph Implementation

This module provides the DataAnalysisAgent using LangGraph's create_react_agent pattern.
The agent is responsible for schema exploration, data understanding, and creating detailed query plans.
"""

from typing import Any, List, Optional, Dict
from pydantic import ConfigDict, Field, Json
import json

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState
from langgraph.prebuilt import create_react_agent

from doorbeen.core.assistants.analysis.sql.tools.data_analysis import (
    get_schema,
    get_table_sample_data,
    create_query_plan,
    data_analysis_pre_hook,
    data_analysis_post_hook,
    notify_outputs
)
from doorbeen.core.assistants.analysis.sql.supervisor.tools import (
    get_objective_from_state,
    get_schema_context,
    update_schema_context,
    add_handoff_context,
    get_current_status
)
from doorbeen.core.models.provider import ModelHandler


class QueryPlanDetails(TSModel):
    """Schema for query plan details."""
    strategy: str = Field(description="High-level approach description")
    primary_table: str = Field(description="Main table name")
    required_columns: List[str] = Field(description="List of required column names", default_factory=list)
    expected_result_type: str = Field(description="Description of expected query results")
    model_config = ConfigDict(extra="forbid")


class DataAnalysisResponse(TSModel):
    """Structured response schema for the Data Analysis Agent."""
    schema_summary: str = Field(description="A comprehensive summary of the database schema relevant to the user's query")
    relevant_tables: List[str] = Field(description="List of table names that are relevant to answering the user's question", default_factory=list)
    query_plan: QueryPlanDetails = Field(description="Detailed plan for query generation including strategy, key columns, filters, and examples")
    query_strategy: str = Field(description="High-level strategy description for how to approach the query")
    
    model_config = ConfigDict(extra="forbid")


DATA_ANALYSIS_AGENT_PROMPT = """
You are a Data Analysis Agent specialized in understanding database schemas and user queries.

Your role is to:
1. **Analyze the database schema** to understand available tables, columns, and relationships
2. **Identify relevant tables** based on the user's query by matching query concepts to table/column names
3. **Collect sample data** from the most relevant tables to understand data patterns
4. **Create a comprehensive analysis plan** that guides the Query Generator

## Core Responsibilities:

### 1. Schema Understanding
- Retrieve and analyze the complete database schema
- Understand table relationships and foreign keys
- Identify primary keys and data types

### 2. Intelligent Table Selection
- Analyze the user's query to identify key concepts and entities
- Match query concepts to table names and column names in the schema
- Prioritize tables based on relevance to the query
- Use EXACT table names from the schema - never modify or assume table names

### 3. Contextual Data Sampling
- Collect sample data from the most relevant tables
- Understand data patterns and formats
- Identify potential data quality issues

### 4. Analysis Planning
- Create a comprehensive plan for query generation
- Provide clear guidance on which tables to use
- Suggest appropriate joins and filtering strategies

## Workflow:
1. **get_schema**: Retrieve complete database schema
2. **analyze_relevant_tables**: Intelligently identify tables relevant to the user query
3. **get_table_sample_data**: Collect sample data from relevant tables
4. **get_comprehensive_context**: Prepare comprehensive context for Query Generator

## Important Rules:
- **NEVER modify table names** - use exact names from the schema
- **Always validate table existence** before making recommendations
- **Focus on query relevance** when selecting tables
- **Provide clear reasoning** for table selection decisions
- **Be database-agnostic** - work with any database type and schema

## Tools Available:
- `get_schema`: Retrieve database schema information
- `analyze_relevant_tables`: Analyze user query against schema to identify relevant tables
- `get_table_sample_data`: Collect sample data from tables
- `get_comprehensive_context`: Prepare comprehensive context for next agent

Start by retrieving the schema, then analyze which tables are relevant to the user's query before proceeding with data sampling.
"""


def create_data_analysis_agent(
    name: str,
    handler: ModelHandler,
):
    """Creates a data analysis agent with enhanced query planning capabilities."""
    system_message = """
You are a database schema expert and query planning specialist. Your role is to:

1. **Explore Database Schema**: Understand table structures, relationships, and data types
2. **Analyze User Requirements**: Break down the user's question into data requirements
3. **Create Detailed Query Plans**: Provide comprehensive plans for query generation
4. **Gather Table Examples**: Get sample data to understand actual data formats

**ENHANCED WORKFLOW:**

1. **Schema Exploration**:
   - Use `get_schema` to explore database structure
   - Identify relevant tables for the user's question
   - Analyze column data types and constraints

2. **Sample Data Collection**:
   - Use `get_table_sample_data` for each relevant table (max 5 rows per table)
   - Understand actual data formats, especially for dates/times
   - Identify patterns in data storage

3. **Query Plan Creation**:
   - Use `create_query_plan` to store detailed strategy
   - Specify exact column names and data types
   - Provide filtering logic based on actual data formats
   - Include JOIN requirements if multiple tables needed
   - Add specific instructions for date/time handling

4. **Transfer to QueryGenerator**:
   - Once schema exploration and query planning is complete, transfer control
   - Use the appropriate transfer tool to hand off to QueryGenerator
   - Ensure all context (schema, examples, plan) is stored in state

5. **MANDATORY FINAL STEP**:
   - **ALWAYS call `notify_outputs` as the final step** after completing all analysis
   - This tool provides important context about what was accomplished
   - Do not skip this step - it is required for proper workflow tracking

**QUERY PLAN STRUCTURE:**
Your query_plan should include:
- strategy: High-level approach description
- primary_table: Main table name
- required_columns: List of exact column names needed
- expected_result_type: Description of what the query should return

**CRITICAL REQUIREMENTS:**
- **NEVER assume column names** - always verify in schema
- **Always get sample data** to understand actual formats
- **Be specific about data types** and how to handle them
- **Include exact column names** from the schema
- **Provide filtering examples** based on actual data
- **Note any special handling** needed (dates, timezones, etc.)
- **ALWAYS call `notify_outputs` at the end** - this is mandatory

**EXAMPLE ANALYSIS:**
For "When did I fall asleep on July 3rd?":
- Identify sleep-related tables
- Find date/time columns (bedtime, sleep_date, etc.)
- Check actual date formats in sample data
- Verify timezone storage format
- Create specific filtering strategy
- Warn about potential column name issues

Remember: Your query plan will be used by QueryGenerator to create SQL. Be extremely specific and accurate about schema details. Always end with `notify_outputs` to complete the workflow.
"""
    
    tools = [
        get_objective_from_state,
        get_schema_context,
        update_schema_context,
        get_schema,
        get_table_sample_data,
        create_query_plan,
        add_handoff_context,
        get_current_status,
        notify_outputs
    ]
    
    return create_react_agent(
        name=name,
        model=handler.model,
        tools=tools,
        prompt=system_message,
        state_schema=SQLSupervisorState,
        pre_model_hook=data_analysis_pre_hook,
        post_model_hook=data_analysis_post_hook,
        response_format=DataAnalysisResponse
    ) 