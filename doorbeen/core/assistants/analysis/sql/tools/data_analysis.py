import json
import logging
from typing import Dict, Any, List, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing_extensions import Annotated

from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.assistants.analysis.sql.instructions.database import get_database_specific_instructions
from doorbeen.core.models.provider import ModelHandler

logger = logging.getLogger(__name__)


@tool
async def get_schema(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Retrieve and analyze database schema information.
    
    Args:
        config: Configuration containing database connection
        state: Current state
        tool_call_id: Tool call ID for the ToolMessage
        
    Returns:
        Command: Updated state with schema context
    """
    try:
        logger.info("[GET_SCHEMA] Retrieving database schema...")
        
        # Emit progress event
        progress_event = {
            "type": "agent:progress",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": "Connecting to database and retrieving schema...",
                "content": "🔍 Analyzing database structure",
                "progress": 10
            }
        }
        
        # Get database connection from config
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection")
        
        if not connection:
            error_msg = "Database connection not available"
            logger.error(f"[GET_SCHEMA] ❌ {error_msg}")
            
            tool_message = ToolMessage(
                content=f"❌ {error_msg}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [progress_event],
                    "error": {
                        "type": "connection_error",
                        "message": error_msg,
                        "details": "No connection found in configuration"
                    }
                }
            )
        
        # Emit schema retrieval progress
        schema_progress_event = {
            "type": "agent:progress",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": "Retrieving database schema information...",
                "content": "📊 Fetching table and column information",
                "progress": 30
            }
        }
        
        # Get schema information
        schema = connection.get_schema()
        
        # Detect database type from connection
        database_type = "unknown"
        if hasattr(connection, 'credentials') and hasattr(connection.credentials, 'dialect'):
            database_type = connection.credentials.dialect.value
        elif hasattr(connection, 'engine') and connection.engine:
            # Try to detect from engine URL
            engine_url = str(connection.engine.url)
            if 'postgresql' in engine_url:
                database_type = "postgresql"
            elif 'mysql' in engine_url:
                database_type = "mysql"
            elif 'sqlite' in engine_url:
                database_type = "sqlite"

        # Emit processing progress
        processing_progress_event = {
            "type": "agent:progress",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": f"Processing schema for {database_type} database...",
                "content": "⚙️ Analyzing table structures and relationships",
                "progress": 60
            }
        }

        # Process schema for context
        schema_context = {
            "tables": [],
            "total_tables": 0,
            "database_type": database_type
        }
            
        # Handle both list and dict cases for schema.tables
        if hasattr(schema, 'tables'):
            if isinstance(schema.tables, list):
                # It's a list of TableSchema objects
                for table in schema.tables:
                    table_info = {
                        "name": table.name,
                        "columns": []
                    }

                    # Add column information
                    for column in table.columns:
                        column_info = {
                            "name": column.name,
                            "type": column.type,
                            "nullable": getattr(column, 'nullable', True),
                            "primary_key": getattr(column, 'primary_key', False)
                        }
                        table_info["columns"].append(column_info)

                    # Add foreign key information if available
                    if hasattr(table, 'foreign_keys') and table.foreign_keys:
                        table_info["foreign_keys"] = []
                        for fk in table.foreign_keys:
                            fk_info = {
                                "column": fk.column,
                                "referenced_table": fk.referenced_table,
                                "referenced_column": fk.referenced_column
                            }
                            table_info["foreign_keys"].append(fk_info)

                    schema_context["tables"].append(table_info)
                    schema_context["total_tables"] = len(schema.tables)
            elif isinstance(schema.tables, dict):
                # It's a dictionary - convert to list format
                for table_name, table_info in schema.tables.items():
                                table_data = {
                                    "name": table_name,
                                    "columns": table_info.get("columns", [])
                                }
                                schema_context["tables"].append(table_data)
                                schema_context["total_tables"] = len(schema.tables)

        # Create schema summary
        schema_summary = f"Database contains {schema_context['total_tables']} tables"
        if schema_context["tables"]:
            table_names = [table["name"] for table in schema_context["tables"]]
            schema_summary += f": {', '.join(table_names[:5])}"
            if len(table_names) > 5:
                schema_summary += f" and {len(table_names) - 5} more"
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": f"Schema analysis complete - found {schema_context['total_tables']} tables",
                "content": f"✅ Analyzed {schema_context['total_tables']} tables in {database_type} database",
                "progress": 100
            }
        }

        logger.info(f"[GET_SCHEMA] ✅ Retrieved schema with {schema_context['total_tables']} tables for {database_type} database")

        tool_message = ToolMessage(
            content=f"✅ Retrieved schema with {schema_context['total_tables']} tables for {database_type} database",
            tool_call_id=tool_call_id
        )

        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [progress_event, schema_progress_event, processing_progress_event, completion_progress_event],
                "schema_context": schema_context,
            "schema_summary": schema_summary,
                "database_dialect": database_type
            }
        )
    except Exception as e:
        error_msg = f"Error retrieving schema: {str(e)}"
        logger.error(f"[GET_SCHEMA] ❌ {error_msg}")
        
        error_progress_event = {
            "type": "agent:error",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": f"Schema retrieval failed: {error_msg}",
                "content": f"❌ Failed to retrieve database schema",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ {error_msg}",
            tool_call_id=tool_call_id
        )
    
    return Command(
        update={
            "messages": [tool_message],
            "agent_lifecycle_events": [error_progress_event],
            "error": {
                "type": "schema_error",
                "message": error_msg,
                "details": str(e)
            }
        }
    )


@tool
async def get_table_sample_data(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Get sample data from relevant tables for context.
    
    Args:
        config: Configuration containing database connection
        state: Current state containing schema and table information
        tool_call_id: Tool call ID for the ToolMessage
        
    Returns:
        Command: Updated state with table examples
    """
    try:
        logger.info("[GET_SAMPLE_DATA] Retrieving sample data from tables...")
        
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": "Starting sample data collection...",
                "content": "🔍 Preparing to sample data from tables",
                "progress": 10
            }
        }
        
        # Get database connection from config
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection")
        
        if not connection:
            error_msg = "Database connection not available"
            logger.error(f"[GET_SAMPLE_DATA] ❌ {error_msg}")
            
            tool_message = ToolMessage(
                content=f"❌ {error_msg}",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event],
                    "error": {
                        "type": "connection_error",
                        "message": error_msg,
                        "details": "No connection found in configuration"
                    },
                    "table_examples": {},
                    "sample_data_cache": {}
                }
            )
        
        # Get relevant tables from state
        schema_context = state.get("schema_context", {})
        tables = schema_context.get("tables", [])
        
        if not tables:
            logger.warning("[GET_SAMPLE_DATA] ⚠️ No tables found in schema context")
            
            no_tables_progress_event = {
                "type": "agent:warning",
                "name": "DataAnalysis",
                "data": {
                    "scope": "DataAnalysis",
                    "description": "No tables found in schema context",
                    "content": "⚠️ No tables available for sampling",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No tables found in schema context",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, no_tables_progress_event],
                    "table_examples": {},
                    "sample_data_cache": {}
                }
            )
        
        table_examples = {}
        sample_data_cache = {}
        progress_events = [start_progress_event]
        
        # Sample data from each table (limit to first 5 tables to avoid overwhelming context)
        tables_to_sample = tables[:5]
        total_tables = len(tables_to_sample)
        
        for i, table_info in enumerate(tables_to_sample):
            table_name = table_info["name"]
            
            # Emit progress for current table
            table_progress = 20 + (i * 60 // total_tables)
            table_progress_event = {
                "type": "agent:progress",
                "name": "DataAnalysis",
                "data": {
                    "scope": "DataAnalysis",
                    "description": f"Sampling data from table '{table_name}' ({i+1}/{total_tables})",
                    "content": f"📊 Collecting sample data from {table_name}",
                    "progress": table_progress
                }
            }
            progress_events.append(table_progress_event)
            
        try:
            # Get sample data (limit to 3 rows for context)
            sample_query = f"SELECT * FROM {table_name} LIMIT 3"

            # Execute with transaction handling
            result = connection.query(sample_query)

            if result and len(result) > 0:
                # Convert result to list of dictionaries
                sample_data = []
                for row in result:
                    if isinstance(row, dict):
                        sample_data.append(row)
                    else:
                        # Handle tuple/list results - convert to dict using column names
                        columns = [col["name"] for col in table_info.get("columns", [])]
                        if columns and len(row) == len(columns):
                            sample_data.append(dict(zip(columns, row)))
                        else:
                            # Fallback: create generic column names
                            sample_data.append({f"col_{i}": val for i, val in enumerate(row)})

                table_examples[table_name] = sample_data
                sample_data_cache[table_name] = {
                    "row_count": len(sample_data),
                    "query_used": sample_query,
                    "status": "success"
                }

                # Emit success event for this table
                success_event = {
                    "type": "agent:progress",
                    "name": "DataAnalysis",
                    "data": {
                        "scope": "DataAnalysis",
                        "description": f"Successfully sampled {len(sample_data)} rows from {table_name}",
                        "content": f"✅ {table_name}: {len(sample_data)} sample rows",
                        "progress": table_progress + 5
                    }
                }
                progress_events.append(success_event)

                logger.info(f"[GET_SAMPLE_DATA] ✅ Retrieved {len(sample_data)} sample rows from {table_name}")
            else:
                logger.info(f"[GET_SAMPLE_DATA] ℹ️ No data found in table {table_name}")
                table_examples[table_name] = []
                sample_data_cache[table_name] = {
                    "row_count": 0,
                    "query_used": sample_query,
                    "status": "empty"
                }

                # Emit empty table event
                empty_event = {
                    "type": "agent:warning",
                    "name": "DataAnalysis",
                    "data": {
                        "scope": "DataAnalysis",
                        "description": f"Table {table_name} is empty",
                        "content": f"ℹ️ {table_name}: No data found",
                        "progress": table_progress + 5
                    }
                }
                progress_events.append(empty_event)
        except Exception as query_error:
            logger.warning(f"[GET_SAMPLE_DATA] ⚠️ Could not sample {table_name}: {str(query_error)}")

            # Try to recover with table name correction
            corrected_name = _correct_table_name(table_name, tables)
            if corrected_name and corrected_name != table_name:
                try:
                    corrected_query = f"SELECT * FROM {corrected_name} LIMIT 3"
                    result = connection.query(corrected_query)

                    if result and len(result) > 0:
                        sample_data = []
                        for row in result:
                            if isinstance(row, dict):
                                sample_data.append(row)
                            else:
                                columns = [col["name"] for col in table_info.get("columns", [])]
                                if columns and len(row) == len(columns):
                                    sample_data.append(dict(zip(columns, row)))
                                else:
                                    sample_data.append({f"col_{i}": val for i, val in enumerate(row)})

                        table_examples[corrected_name] = sample_data
                        sample_data_cache[corrected_name] = {
                            "row_count": len(sample_data),
                            "query_used": corrected_query,
                            "status": "success_corrected",
                            "original_name": table_name
                        }

                        # Emit correction success event
                        correction_event = {
                            "type": "agent:progress",
                            "name": "DataAnalysis",
                            "data": {
                                "scope": "DataAnalysis",
                                "description": f"Corrected table name {table_name} → {corrected_name}",
                                "content": f"🔄 {corrected_name}: {len(sample_data)} rows (corrected)",
                                "progress": table_progress + 5
                            }
                        }
                        progress_events.append(correction_event)

                        logger.info(f"[GET_SAMPLE_DATA] ✅ Retrieved {len(sample_data)} sample rows from {corrected_name} (corrected from {table_name})")
                    else:
                        table_examples[table_name] = []
                        sample_data_cache[table_name] = {
                            "row_count": 0,
                            "query_used": sample_query,
                            "status": "failed",
                            "error": str(query_error)
                        }
                except Exception as correction_error:
                    logger.warning(f"[GET_SAMPLE_DATA] ⚠️ Correction attempt failed for {table_name}: {str(correction_error)}")
                    table_examples[table_name] = []
                    sample_data_cache[table_name] = {
                        "row_count": 0,
                        "query_used": sample_query,
                        "status": "failed",
                        "error": str(query_error)
                    }
            else:
                table_examples[table_name] = []
                sample_data_cache[table_name] = {
                    "row_count": 0,
                    "query_used": sample_query,
                    "status": "failed",
                    "error": str(query_error)
                }

                # Emit error event for this table
                error_event = {
                    "type": "agent:warning",
                    "name": "DataAnalysis",
                    "data": {
                        "scope": "DataAnalysis",
                        "description": f"Failed to sample {table_name}: {str(query_error)[:50]}...",
                        "content": f"⚠️ {table_name}: Sampling failed",
                        "progress": table_progress + 5
                    }
                }
                progress_events.append(error_event)
        
        total_sampled = sum(1 for examples in table_examples.values() if examples)
        
        # Emit completion event
        completion_event = {
            "type": "agent:progress",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": f"Sample data collection complete - {total_sampled}/{total_tables} tables sampled",
                "content": f"✅ Collected sample data from {total_sampled} out of {total_tables} tables",
                "progress": 100
            }
        }
        progress_events.append(completion_event)
        
        logger.info(f"[GET_SAMPLE_DATA] ✅ Successfully sampled data from {total_sampled}/{len(tables[:5])} tables")
        
        tool_message = ToolMessage(
            content=f"✅ Successfully sampled data from {total_sampled}/{len(tables[:5])} tables",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": progress_events,
                "table_examples": table_examples,
                "sample_data_cache": sample_data_cache
            }
        )         
    except Exception as e:
        error_msg = f"Error retrieving sample data: {str(e)}"
        logger.error(f"[GET_SAMPLE_DATA] ❌ {error_msg}")
        
        error_event = {
            "type": "agent:error",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": f"Sample data collection failed: {error_msg}",
                "content": "❌ Failed to collect sample data",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ {error_msg}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {
                    "type": "sample_data_error",
                    "message": error_msg,
                    "details": str(e)
                },
                "table_examples": {},
                "sample_data_cache": {}
            }
        )


@tool
async def create_query_plan(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Create a detailed query plan based on the user's request and available schema.
    
    Args:
        config: Configuration containing database connection and model
        state: Current state containing user input, schema, and sample data
        tool_call_id: Tool call ID for the ToolMessage
        
    Returns:
        Command: Updated state with query plan
    """
    try:
        logger.info("[CREATE_QUERY_PLAN] Creating intelligent query plan...")
        
        # Get user input from state - try multiple possible sources
        user_input = state.get("input", "")
        
        # If input is empty, try to extract from messages
        if not user_input:
            messages = state.get("messages", [])
            for message in messages:
                if hasattr(message, 'content') and hasattr(message, 'type'):
                    if message.type == "human":
                        user_input = message.content
                        break
                elif isinstance(message, dict) and message.get("type") == "human":
                    user_input = message.get("content", "")
                    break
        
        # If still no input, check the first message in the conversation
        if not user_input and messages:
            first_message = messages[0]
            if hasattr(first_message, 'content'):
                user_input = first_message.content
            elif isinstance(first_message, dict):
                user_input = first_message.get("content", "")
        
        logger.info(f"[CREATE_QUERY_PLAN] User input found: '{user_input[:100]}...' (length: {len(user_input)})")
        
        if not user_input:
            logger.warning("[CREATE_QUERY_PLAN] ⚠️ No user input provided")
            
            tool_message = ToolMessage(
                content="⚠️ No user input provided",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "query_plan": {
                        "status": "failed",
                        "error": "No user input provided"
                    }
                }
            )

        # Get schema context and sample data
        schema_context = state.get("schema_context", {})
        table_examples = state.get("table_examples", {})
        database_type = schema_context.get("database_type", "unknown")
        
        # Get model handler from config
        configuration = config.get("configurable", {})
        handler = configuration.get("handler")
        
        if not handler:
            logger.error("[CREATE_QUERY_PLAN] ❌ No model handler available")
            tool_message = ToolMessage(
                content="❌ No model handler available for query planning",
                tool_call_id=tool_call_id
            )
            return Command(
                update={
                    "messages": [tool_message],
                    "query_plan": {"status": "failed", "error": "No model handler available"}
                }
            )

        # Prepare comprehensive schema information for the model
        available_tables = schema_context.get("tables", [])
        
        # Build detailed schema description
        schema_description = []
        for table in available_tables:
            table_desc = f"Table: {table['name']}\n"
            
            # Add columns with details
            columns = []
            for col in table.get("columns", []):
                col_desc = f"  - {col['name']} ({col['type']})"
                if col.get("primary_key"):
                    col_desc += " [PRIMARY KEY]"
                if not col.get("nullable", True):
                    col_desc += " [NOT NULL]"
                columns.append(col_desc)
            
            table_desc += "\n".join(columns)
            
            # Add foreign keys if available
            if table.get("foreign_keys"):
                table_desc += "\n  Foreign Keys:"
                for fk in table["foreign_keys"]:
                    table_desc += f"\n    - {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}"
            
            # Add sample data if available
            if table['name'] in table_examples:
                sample_data = table_examples[table['name']]
                if sample_data:
                    table_desc += f"\n  Sample Data ({len(sample_data)} rows):"
                    # Show first few rows with all columns for better context
                    for i, sample_row in enumerate(sample_data[:2]):  # Show first 2 rows
                        table_desc += f"\n    Row {i+1}:"
                        for key, value in sample_row.items():
                            # Show the actual value and its type/format
                            value_str = str(value)[:100] if value is not None else "NULL"
                            table_desc += f"\n      - {key}: {value_str}"
                    
                    # Add data pattern analysis
                    table_desc += f"\n  Data Patterns:"
                    # Analyze unique values for key columns
                    for col in table.get("columns", []):
                        col_name = col["name"]
                        if sample_data and col_name in sample_data[0]:
                            unique_values = list(set(str(row.get(col_name, "")) for row in sample_data))[:5]
                            if len(unique_values) > 0:
                                table_desc += f"\n    - {col_name} examples: {', '.join(unique_values)}"
            
            schema_description.append(table_desc)

        # Create comprehensive planning prompt
        planning_prompt = f"""
You are an expert database analyst. Analyze the user query against the database schema to create a detailed query execution plan.

USER QUERY: {user_input}

DATABASE SCHEMA ({database_type} database):
{chr(10).join(schema_description)}

TASK: Create a comprehensive query plan that identifies:
1. Which tables are relevant to answer the user's query
2. Which specific columns are needed
3. What type of analysis is required
4. How tables should be joined (if multiple tables needed)
5. What filtering, aggregation, or sorting is needed
6. Expected output format

ANALYSIS REQUIREMENTS:
- Be precise about table and column selection
- Only include tables that are directly relevant to the query
- Consider data relationships and foreign keys
- Think about temporal aspects (dates, times) if mentioned
- Consider aggregation needs (counts, sums, averages)
- Be database-agnostic in your approach

Respond with a JSON object containing:
{{
    "relevant_tables": [
        {{
            "table_name": "exact_table_name_from_schema",
            "relevance_reason": "why this table is needed",
            "key_columns": ["column1", "column2"],
            "role": "primary|supporting|lookup"
        }}
    ],
    "query_strategy": "data_retrieval|aggregation|temporal_analysis|join_analysis|statistical_analysis",
    "analysis_type": "simple_select|filtered_select|aggregated_data|time_series|multi_table_join",
    "required_operations": [
        "operation1", "operation2"
    ],
    "expected_joins": [
        {{
            "left_table": "table1",
            "right_table": "table2", 
            "join_condition": "table1.fk = table2.pk",
            "join_type": "INNER|LEFT|RIGHT"
        }}
    ],
    "filtering_criteria": [
        {{
            "column": "column_name",
            "condition": "condition_description",
            "value_type": "string|number|date|boolean"
        }}
    ],
    "aggregation_needs": {{
        "required": true|false,
        "functions": ["COUNT", "SUM", "AVG", "MAX", "MIN"],
        "group_by_columns": ["column1", "column2"]
    }},
    "temporal_aspects": {{
        "has_time_component": true|false,
        "time_columns": ["column1"],
        "time_range_needed": true|false,
        "time_format": "timestamp|date|time"
    }},
    "complexity_assessment": "low|medium|high",
    "estimated_result_size": "small|medium|large",
    "query_description": "Natural language description of what the query will do",
    "success_criteria": "How to determine if the query answered the user's question"
}}

CRITICAL: Use EXACT table and column names from the schema. Do not modify or assume names.
"""

        # Emit progress event
        progress_event = {
            "type": "agent:progress",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": "Creating intelligent query plan using model analysis...",
                "content": "🧠 Analyzing query requirements against database schema",
                "progress": 70
            }
        }

        # Get analysis from model
        response = await handler.model.ainvoke(planning_prompt)
        
        try:
            query_plan = json.loads(response.content)
            
            # Validate that all referenced tables exist in schema
            valid_table_names = {t["name"] for t in available_tables}
            validated_relevant_tables = []
            
            for table_info in query_plan.get("relevant_tables", []):
                table_name = table_info.get("table_name", "")
                if table_name in valid_table_names:
                    validated_relevant_tables.append(table_info)
                else:
                    logger.warning(f"[CREATE_QUERY_PLAN] ⚠️ Invalid table name in plan: {table_name}")
            
            # Update the plan with validated tables
            query_plan["relevant_tables"] = validated_relevant_tables
            
            # Add metadata
            query_plan["user_request"] = user_input
            query_plan["database_type"] = database_type
            query_plan["total_available_tables"] = len(available_tables)
            query_plan["selected_tables_count"] = len(validated_relevant_tables)
            query_plan["planning_timestamp"] = str(logger.info.__module__)  # Simple timestamp
            query_plan["status"] = "success"
            
            # Extract relevant table names for easy access
            relevant_table_names = [t["table_name"] for t in validated_relevant_tables]
            
            # Emit completion event
            completion_event = {
                "type": "agent:progress",
                "name": "DataAnalysis",
                "data": {
                    "scope": "DataAnalysis",
                    "description": f"Query plan complete - identified {len(relevant_table_names)} relevant tables",
                    "content": f"✅ Plan: {query_plan.get('query_strategy', 'unknown')} using {', '.join(relevant_table_names)}",
                    "progress": 100
                }
            }
            
            logger.info(f"[CREATE_QUERY_PLAN] ✅ Created intelligent plan: {query_plan.get('query_strategy', 'unknown')} strategy with {len(relevant_table_names)} tables")
            
            tool_message = ToolMessage(
                content=f"✅ Created intelligent query plan: {query_plan.get('query_strategy', 'unknown')} strategy with {len(relevant_table_names)} relevant tables",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [progress_event, completion_event],
                    "input": user_input,  # Ensure input is set in state
                    "query_plan": query_plan,
                    "relevant_tables": relevant_table_names,
                    "query_strategy": query_plan.get("query_strategy", "data_analysis")
                }
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"[CREATE_QUERY_PLAN] ❌ Failed to parse model response: {e}")
            
            # Fallback: create basic plan
            fallback_plan = {
                "user_request": user_input,
                "relevant_tables": [{"table_name": table["name"], "relevance_reason": "Fallback selection", "key_columns": [col["name"] for col in table.get("columns", [])[:3]], "role": "primary"} for table in available_tables[:2]],
                "query_strategy": "data_retrieval",
                "analysis_type": "simple_select",
                "complexity_assessment": "medium",
                "query_description": f"Retrieve data to answer: {user_input}",
                "status": "fallback",
                "error": "Model response parsing failed"
            }
            
            tool_message = ToolMessage(
                content="⚠️ Created fallback query plan due to parsing error",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [progress_event],
                    "input": user_input,
                    "query_plan": fallback_plan,
                    "relevant_tables": [t["table_name"] for t in fallback_plan["relevant_tables"]],
                    "query_strategy": "data_retrieval"
                }
            )       
    except Exception as e:
        error_msg = f"Error creating query plan: {str(e)}"
        logger.error(f"[CREATE_QUERY_PLAN] ❌ {error_msg}")
        
        error_event = {
            "type": "agent:error",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": f"Query planning failed: {error_msg}",
                "content": "❌ Failed to create query plan",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ {error_msg}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {
                    "type": "query_plan_error",
                    "message": error_msg,
                    "details": str(e)
                },
                "query_plan": {
                    "status": "failed",
                    "error": error_msg
                }
            }
        )


@tool
async def get_comprehensive_context(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Compile comprehensive context for the query generator.
    
    Args:
        config: Configuration containing database connection
        state: Current state with schema, samples, and query plan
        tool_call_id: Tool call ID for the ToolMessage
        
    Returns:
        Command: Updated state with comprehensive context
    """
    try:
        logger.info("[GET_COMPREHENSIVE_CONTEXT] Compiling comprehensive context...")
        
        # Gather all available context
        schema_context = state.get("schema_context", {})
        table_examples = state.get("table_examples", {})
        query_plan = state.get("query_plan", {})
        user_input = state.get("input", "")
        
        # Build comprehensive context
        comprehensive_context = {
            "user_request": user_input,
            "database_info": {
                "total_tables": schema_context.get("total_tables", 0),
                "database_type": schema_context.get("database_type", "unknown"),
                "tables": schema_context.get("tables", [])
            },
            "sample_data": table_examples,
            "query_plan": query_plan,
            "instructions": get_database_specific_instructions("postgresql"),
            "context_quality": "high" if all([schema_context, table_examples, query_plan]) else "medium"
        }
        
        # Add data analysis context
        if table_examples:
            comprehensive_context["data_insights"] = {
                "tables_with_data": [name for name, data in table_examples.items() if data],
                "empty_tables": [name for name, data in table_examples.items() if not data],
                "total_sample_rows": sum(len(data) for data in table_examples.values())
            }
        
        # Add query generation hints
        comprehensive_context["generation_hints"] = {
            "use_table_aliases": True,
            "add_limit_clause": True,
            "handle_nulls": True,
            "validate_syntax": True
        }
        
        logger.info(f"[GET_COMPREHENSIVE_CONTEXT] ✅ Compiled comprehensive context with {comprehensive_context['context_quality']} quality")
        
        tool_message = ToolMessage(
            content=f"✅ Compiled comprehensive context with {comprehensive_context['context_quality']} quality",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "comprehensive_context": comprehensive_context
            }
        )
        
    except Exception as e:
        error_msg = f"Error compiling comprehensive context: {str(e)}"
        logger.error(f"[GET_COMPREHENSIVE_CONTEXT] ❌ {error_msg}")
        
        tool_message = ToolMessage(
            content=f"❌ {error_msg}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "error": {
                    "type": "context_compilation_error",
                    "message": error_msg,
                    "details": str(e)
                },
                "comprehensive_context": {
                    "status": "failed",
                    "error": error_msg
                }
            }
        )


@tool
async def analyze_relevant_tables(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Analyze user input against database schema to identify relevant tables.
    
    Args:
        config: Configuration containing database connection and model
        state: Current state containing user input and schema
        tool_call_id: Tool call ID for the ToolMessage
        
    Returns:
        Command: Updated state with relevant tables analysis
    """
    try:
        logger.info("[ANALYZE_RELEVANT_TABLES] Analyzing user input against schema...")
        
        # Get user input from state
        user_input = state.get("input", "")
        if not user_input:
            messages = state.get("messages", [])
            for message in messages:
                if hasattr(message, 'content') and hasattr(message, 'type'):
                    if message.type == "human":
                        user_input = message.content
                        break
                elif isinstance(message, dict) and message.get("type") == "human":
                    user_input = message.get("content", "")
                    break
        
        if not user_input:
            logger.warning("[ANALYZE_RELEVANT_TABLES] ⚠️ No user input found")
            tool_message = ToolMessage(
                content="⚠️ No user input found for table analysis",
                tool_call_id=tool_call_id
            )
            return Command(
                update={
                    "messages": [tool_message],
                    "relevant_tables": [],
                    "table_analysis": {"status": "failed", "error": "No user input"}
                }
            )
        
        # Get schema context
        schema_context = state.get("schema_context", {})
        tables = schema_context.get("tables", [])
        
        if not tables:
            logger.warning("[ANALYZE_RELEVANT_TABLES] ⚠️ No tables found in schema")
            tool_message = ToolMessage(
                content="⚠️ No tables found in schema",
                tool_call_id=tool_call_id
            )
            return Command(
                update={
                    "messages": [tool_message],
                    "relevant_tables": [],
                    "table_analysis": {"status": "failed", "error": "No tables in schema"}
                }
            )
        
        # Get model handler from config
        configuration = config.get("configurable", {})
        handler = configuration.get("handler")
        
        if not handler:
            logger.error("[ANALYZE_RELEVANT_TABLES] ❌ No model handler available")
            tool_message = ToolMessage(
                content="❌ No model handler available for table analysis",
                tool_call_id=tool_call_id
            )
            return Command(
                update={
                    "messages": [tool_message],
                    "relevant_tables": [],
                    "table_analysis": {"status": "failed", "error": "No model handler available"}
                }
            )
        
        # Prepare schema summary for analysis
        schema_summary = []
        for table in tables:
            table_info = {
                "table_name": table["name"],
                "columns": []
            }
            
            for col in table.get("columns", []):
                col_info = f"{col['name']} ({col['type']})"
                if col.get("primary_key"):
                    col_info += " [PRIMARY KEY]"
                table_info["columns"].append(col_info)
            
            # Add foreign keys if available
            if table.get("foreign_keys"):
                table_info["foreign_keys"] = []
                for fk in table["foreign_keys"]:
                    fk_info = f"{fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}"
                    table_info["foreign_keys"].append(fk_info)
            
            schema_summary.append(table_info)
        
        # Create analysis prompt
        analysis_prompt = f"""
Analyze the following user query against the database schema to identify the most relevant tables:

USER QUERY: {user_input}

DATABASE SCHEMA:
{chr(10).join([f"Table: {t['table_name']}" + chr(10) + f"Columns: {', '.join(t['columns'])}" + (chr(10) + f"Foreign Keys: {', '.join(t.get('foreign_keys', []))}" if t.get('foreign_keys') else "") for t in schema_summary])}

Task: Identify which tables are most relevant to answer the user's query. Consider:
1. Table names that might relate to the query topic
2. Column names that match concepts in the query
3. Data types that would be needed for the analysis
4. Relationships between tables that might be required

Respond with a JSON object containing:
{{
    "relevant_tables": [
        {{
            "table_name": "exact_table_name",
            "relevance_score": 0.9,
            "reasoning": "why this table is relevant",
            "key_columns": ["column1", "column2"]
        }}
    ],
    "analysis_summary": "brief summary of the analysis"
}}

IMPORTANT: Use EXACT table names from the schema. Do not modify or assume table names.
"""
        
        # Emit progress event
        progress_event = {
            "type": "agent:progress",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": "Analyzing user query against database schema...",
                "content": "🔍 Identifying relevant tables for the query",
                "progress": 50
            }
        }
        
        # Get analysis from model
        response = await handler.model.ainvoke(analysis_prompt)
        
        try:
            import json
            analysis_result = json.loads(response.content)
            
            relevant_tables = analysis_result.get("relevant_tables", [])
            analysis_summary = analysis_result.get("analysis_summary", "")
            
            # Validate that table names exist in schema
            valid_table_names = {t["name"] for t in tables}
            validated_tables = []
            
            for table_info in relevant_tables:
                table_name = table_info.get("table_name", "")
                if table_name in valid_table_names:
                    validated_tables.append(table_info)
                else:
                    logger.warning(f"[ANALYZE_RELEVANT_TABLES] ⚠️ Invalid table name suggested: {table_name}")
            
            # Emit completion event
            completion_event = {
                "type": "agent:progress",
                "name": "DataAnalysis",
                "data": {
                    "scope": "DataAnalysis",
                    "description": f"Table analysis complete - identified {len(validated_tables)} relevant tables",
                    "content": f"✅ Found {len(validated_tables)} relevant tables: {', '.join([t['table_name'] for t in validated_tables])}",
                    "progress": 100
                }
            }
            
            logger.info(f"[ANALYZE_RELEVANT_TABLES] ✅ Identified {len(validated_tables)} relevant tables")
            
            tool_message = ToolMessage(
                content=f"✅ Identified {len(validated_tables)} relevant tables for analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [progress_event, completion_event],
                    "relevant_tables": validated_tables,
                    "table_analysis": {
                        "status": "success",
                        "summary": analysis_summary,
                        "total_tables_analyzed": len(tables),
                        "relevant_tables_found": len(validated_tables)
                    }
                }
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"[ANALYZE_RELEVANT_TABLES] ❌ Failed to parse model response: {e}")
            
            # Fallback: return all tables with low relevance
            fallback_tables = [
                {
                    "table_name": table["name"],
                    "relevance_score": 0.5,
                    "reasoning": "Fallback analysis - model response parsing failed",
                    "key_columns": [col["name"] for col in table.get("columns", [])[:3]]
                }
                for table in tables
            ]
            
            tool_message = ToolMessage(
                content="⚠️ Table analysis completed with fallback method",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [progress_event],
                    "relevant_tables": fallback_tables,
                    "table_analysis": {
                        "status": "fallback",
                        "summary": "Used fallback analysis due to parsing error",
                        "total_tables_analyzed": len(tables),
                        "relevant_tables_found": len(fallback_tables)
                    }
                }
            )
            
    except Exception as e:
        error_msg = f"Error analyzing relevant tables: {str(e)}"
        logger.error(f"[ANALYZE_RELEVANT_TABLES] ❌ {error_msg}")
        
        error_event = {
            "type": "agent:error",
            "name": "DataAnalysis",
            "data": {
                "scope": "DataAnalysis",
                "description": f"Table analysis failed: {error_msg}",
                "content": "❌ Failed to analyze relevant tables",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ {error_msg}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {
                    "type": "table_analysis_error",
                    "message": error_msg,
                    "details": str(e)
                },
                "relevant_tables": [],
                "table_analysis": {"status": "error", "error": error_msg}
            }
        )


def _correct_table_name(table_name: str, available_tables: List[Dict[str, Any]]) -> Optional[str]:
    """
    Attempt to correct table name using fuzzy matching.
    
    Args:
        table_name: Original table name that failed
        available_tables: List of available table information
        
    Returns:
        Corrected table name or None if no match found
    """
    available_names = [table["name"] for table in available_tables]
    
    # Try exact case-insensitive match first
    for name in available_names:
        if name.lower() == table_name.lower():
            return name
    
    # Try partial matching
    for name in available_names:
        if table_name.lower() in name.lower() or name.lower() in table_name.lower():
            return name
    
    # Try with common variations (singular/plural)
    if table_name.endswith('s'):
        singular = table_name[:-1]
        for name in available_names:
            if name.lower() == singular.lower():
                return name
    else:
        plural = table_name + 's'
        for name in available_names:
            if name.lower() == plural.lower():
                return name
    
    return None


def data_analysis_pre_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Pre-model hook for data analysis agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "DataAnalysis",
        "data": {
            "scope": "DataAnalysis",
            "description": "Starting database schema analysis and query planning",
            "content": "🔍 Starting comprehensive database analysis and query planning"
        }
    }
    return {"agent_lifecycle_events": [event]}


def data_analysis_post_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Post-model hook for data analysis agent - emits agent end event"""
    event = {
        "type": "agent:end",
        "name": "DataAnalysis",
        "data": {
            "scope": "DataAnalysis",
            "description": "Completed schema analysis and created detailed query plan",
            "content": "✅ Completed database schema analysis and query planning"
        }
    }
    return {"agent_lifecycle_events": [event]} 