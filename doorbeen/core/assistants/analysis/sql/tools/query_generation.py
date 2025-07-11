import json
import logging
from typing import Dict, Any, List

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing_extensions import Annotated

from doorbeen.core.assistants.analysis.sql.instructions.database import get_database_specific_instructions
from doorbeen.core.assistants.utils.sql import convert_sqlalchemy_rows_to_dict
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from langchain_core.tools import InjectedToolCallId


@tool
async def get_comprehensive_context(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Get comprehensive context including schema, query plan, and sample data for intelligent query generation."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Gathering comprehensive context for query generation...",
                "content": "🔍 Collecting schema, plan, and sample data",
                "progress": 10
            }
        }
        
        user_question = state.get("input", "")
        schema_context = state.get("schema_context", {})
        query_plan = state.get("query_plan", {})
        table_examples = state.get("table_examples", {})
        previous_errors = state.get("previous_query_errors", [])
        zero_result_attempts = state.get("zero_result_attempts", 0)
        
        # Debug logging to understand state contents
        logging.info(f"[GET_COMPREHENSIVE_CONTEXT] State keys: {list(state.keys())}")
        logging.info(f"[GET_COMPREHENSIVE_CONTEXT] Query plan found: {bool(query_plan)}")
        logging.info(f"[GET_COMPREHENSIVE_CONTEXT] Table examples found: {bool(table_examples)}")
        logging.info(f"[GET_COMPREHENSIVE_CONTEXT] Schema context found: {bool(schema_context)}")
        if query_plan:
            logging.info(f"[GET_COMPREHENSIVE_CONTEXT] Query plan: {query_plan}")
        if table_examples:
            logging.info(f"[GET_COMPREHENSIVE_CONTEXT] Table examples keys: {list(table_examples.keys())}")
        
        # Emit context analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Analyzing context - Plan: {bool(query_plan)}, Examples: {bool(table_examples)}",
                "content": f"📊 Context analysis - Plan: {'✅' if query_plan else '❌'}, Examples: {'✅' if table_examples else '❌'}",
                "progress": 40
            }
        }
        
        # Get database dialect for specific instructions
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection")
        database_dialect = state.get("database_dialect", "postgresql")  # Use from state if available
        
        # Emit context compilation progress
        compilation_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Compiling context for {database_dialect} database...",
                "content": f"⚙️ Building comprehensive context for query generation",
                "progress": 70
            }
        }
        
        context = {
            "user_question": user_question,
            "database_dialect": database_dialect,
            "schema_available": bool(schema_context),
            "query_plan_available": bool(query_plan),
            "table_examples_available": bool(table_examples),
            "has_previous_errors": len(previous_errors) > 0,
            "zero_result_attempts": zero_result_attempts,
            "should_be_suspicious": zero_result_attempts > 0,
            
            # Core context data
            "schema_context": schema_context,
            "query_plan": query_plan,
            "table_examples": table_examples,
            "previous_errors": previous_errors[-3:] if previous_errors else [],  # Last 3 errors
            
            # Database-specific instructions
            "database_instructions": get_database_specific_instructions(database_dialect),
            
            # Regeneration guidance
            "regeneration_guidance": _get_regeneration_guidance(zero_result_attempts, previous_errors)
        }
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Context ready - Plan: {bool(query_plan)}, Examples: {bool(table_examples)}",
                "content": f"✅ Context compiled successfully",
                "progress": 100
            }
        }
        
        logging.info(f"[GET_COMPREHENSIVE_CONTEXT] Context prepared - Plan: {bool(query_plan)}, Examples: {bool(table_examples)}, Zero attempts: {zero_result_attempts}")
        
        tool_message = ToolMessage(
            content=f"✅ Retrieved comprehensive context - Plan: {bool(query_plan)}, Examples: {bool(table_examples)}, Zero attempts: {zero_result_attempts}",
            tool_call_id=tool_call_id
        )
        
        # Use Command to update state
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, analysis_progress_event, compilation_progress_event, completion_progress_event],
                "comprehensive_context": context
            }
        )
        
    except Exception as e:
        logging.error(f"[GET_COMPREHENSIVE_CONTEXT] Error: {e}")
        
        error_progress_event = {
            "type": "agent:error",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Context compilation failed: {str(e)}",
                "content": "❌ Failed to compile comprehensive context",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Failed to get comprehensive context: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_progress_event],
                "error": {"type": "context_error", "message": str(e)}
            }
        )


def _get_regeneration_guidance(zero_attempts: int, previous_errors: List[Dict]) -> Dict[str, Any]:
    """Generate guidance for query regeneration based on previous attempts."""
    
    if zero_attempts == 0:
        return {"should_regenerate": False, "reason": "First attempt"}
    
    guidance = {
        "should_regenerate": zero_attempts < 2,  # Allow up to 2 regenerations
        "zero_attempts": zero_attempts,
        "focus_areas": [],
        "specific_checks": []
    }
    
    if zero_attempts == 1:
        guidance["focus_areas"] = [
            "Verify column names exist in schema",
            "Check actual data formats in sample data",
            "Validate filter conditions against sample values",
            "Ensure date/time formats match actual data"
        ]
        guidance["specific_checks"] = [
            "Do the column names in WHERE clause exist in the table?",
            "Are the filter values in the correct format?",
            "Do the sample data examples show different column names or formats?"
        ]
    elif zero_attempts == 2:
        guidance["focus_areas"] = [
            "Reconsider query strategy entirely",
            "Check if data exists for the specified conditions",
            "Consider alternative filtering approaches",
            "Review sample data for patterns"
        ]
        guidance["specific_checks"] = [
            "Is the date format different than expected?",
            "Are there alternative column names for the same data?",
            "Should we use LIKE instead of exact matches?",
            "Are there different data_type values to check?"
        ]
    
    return guidance


@tool
async def generate_draft_query(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Generate a draft SQL query using the comprehensive context and query plan."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Starting SQL query generation...",
                "content": "🚀 Generating SQL query from context and plan",
                "progress": 10
            }
        }
    
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "Model handler not available",
                    "content": "❌ No model handler available for query generation",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ Model handler not available",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "handler_error", "message": "Model handler not available"}
                }
            )
        
        # Get context from state
        comprehensive_context = state.get("comprehensive_context")
        if not comprehensive_context:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "No comprehensive context available",
                    "content": "❌ Missing context for query generation",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ No comprehensive context available",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "context_error", "message": "No comprehensive context available"}
                }
            )
        
        context = comprehensive_context
        query_plan = context.get("query_plan", {})
        
        # Increment generation attempts
        attempt = state.get("generation_attempts", 0) + 1
        
        # Emit prompt preparation progress
        prompt_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Preparing query generation prompt (attempt {attempt})...",
                "content": f"📝 Building prompt with context and examples",
                "progress": 30
            }
        }
        
        logging.info(f"[GENERATE_DRAFT_QUERY] Generating draft query (attempt {attempt})")
        
        # Create enhanced prompt with query plan and context
        prompt = f"""
You are an expert SQL query generator. Generate a DRAFT SQL query based on the comprehensive context provided.

**USER QUESTION:** {context['user_question']}

**QUERY PLAN FROM DATAANALYST:**
{query_plan if query_plan else "No query plan available"}

**SCHEMA CONTEXT:**
{json.dumps(context.get('schema_context', {}), indent=2)}

**TABLE EXAMPLES:**
{json.dumps(context.get('table_examples', {}), indent=2)}

**DATABASE DIALECT:** {context['database_dialect']}

**PREVIOUS ATTEMPTS:** {context['zero_result_attempts']}
{f"**REGENERATION GUIDANCE:** {json.dumps(context['regeneration_guidance'], indent=2)}" if context['should_be_suspicious'] else ""}

**CRITICAL REQUIREMENTS:**
1. **Follow the Query Plan**: Use the strategy and column details from the DataAnalyst
2. **Verify Column Names**: Only use column names that exist in the schema
3. **Use Sample Data**: Match the actual data formats shown in table examples
4. **Be Suspicious of Previous Zero Results**: If this is a regeneration, carefully review what went wrong

**SPECIFIC INSTRUCTIONS:**
- Use EXACT column names from the schema
- Match data formats from sample data examples
- Follow the filtering strategy from the query plan
- Include database-specific syntax for {context['database_dialect']}
- If regenerating, focus on the areas identified in the regeneration guidance

Generate ONLY the SQL query, no explanations.

**BUSINESS CONTEXT FOR DATA USAGE:**
The data you generate will be used to create executive-level business insights following this structure:

## [Business Area] Performance Analysis

**Executive Summary:** [High-level assessment of performance/trends/status]

**Key Business Metrics:**
- [Primary KPI]: [Value and trend direction]
- [Secondary KPI]: [Value and comparison context]  
- [Efficiency Metric]: [Performance indicator]
- [Strategic Metric]: [Long-term health indicator]

**Business Recommendation:** 
[Clear strategic direction based on the data analysis]

**Recommended Actions:**
1. [Immediate tactical action]
2. [Medium-term strategic initiative]
3. [Long-term optimization opportunity]

**DATA REQUIREMENTS FOR BUSINESS INSIGHTS:**
- Include comparison data (current vs previous periods, actual vs targets, segment vs total)
- Provide aggregated metrics suitable for executive reporting
- Ensure data supports trend analysis and performance assessment
- Include sufficient detail for actionable business recommendations
- Structure results to highlight key performance drivers and outliers
"""
        
        # Emit model invocation progress
        model_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Invoking AI model for query generation...",
                "content": f"🤖 Generating SQL query using AI model",
                "progress": 60
            }
        }
        
        response = await handler.model.ainvoke(prompt)
        draft_query = response.content.strip()
        
        # Emit query processing progress
        processing_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Processing and cleaning generated query...",
                "content": "⚙️ Cleaning and formatting SQL query",
                "progress": 80
            }
        }
        
        # Clean up the query (remove markdown formatting)
        if draft_query.startswith("```sql"):
            draft_query = draft_query[6:]
        if draft_query.endswith("```"):
            draft_query = draft_query[:-3]
        draft_query = draft_query.strip()
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Draft query generated successfully (attempt {attempt})",
                "content": f"✅ Generated SQL Query:\n\n```sql\n{draft_query}\n```\n\nQuery Length: {len(draft_query)} characters",
                "progress": 100
            }
        }
        
        logging.info(f"[GENERATE_DRAFT_QUERY] Generated draft query (attempt {attempt}): {draft_query[:100]}...")
        
        tool_message = ToolMessage(
            content=f"✅ Generated draft query (attempt {attempt})",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, prompt_progress_event, model_progress_event, processing_progress_event, completion_progress_event],
            "draft_query": draft_query,
                "generation_attempts": attempt,
                "workflow_stage": "draft"
            }
        )
        
    except Exception as e:
        logging.error(f"[GENERATE_DRAFT_QUERY] Error: {e}")
        
        error_event = {
            "type": "agent:error",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Query generation failed: {str(e)}",
                "content": "❌ Failed to generate SQL query",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Query generation failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "generation_error", "message": str(e)}
            }
        )


@tool
async def validate_draft_query(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Validate the draft query both syntactically and semantically."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Starting comprehensive query validation...",
                "content": "🔍 Validating SQL query syntax and semantics",
                "progress": 10
            }
        }
    
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection")
        handler: ModelHandler = configuration.get("handler")
    
        if not connection:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "Database connection not available",
                    "content": "❌ No database connection for validation",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ Database connection not available",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "connection_error", "message": "Database connection not available"}
                }
            )

        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for semantic validation",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ Model handler not available",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "handler_error", "message": "Model handler not available"}
                }
            )
    
        draft_query = state.get("draft_query")
        if not draft_query:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "No draft query available to validate",
                    "content": "❌ Missing draft query for validation",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ No draft query available to validate",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "query_error", "message": "No draft query available to validate"}
                }
            )
        
        # Increment validation attempts
        attempt = state.get("validation_attempts", 0) + 1
        
        # STEP 1: Syntactic validation
        syntax_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Validating query syntax (attempt {attempt})...",
                "content": f"⚙️ Syntax Validation\n\n**Query Being Validated:**\n```sql\n{draft_query}\n```\n\n**Status:** Checking SQL syntax...",
                "progress": 30
            }
        }
        
        logging.info(f"[VALIDATE_DRAFT_QUERY] Validating draft query (attempt {attempt}): {draft_query}...")
        
        # Use the validate_query method from CommonSQLClient
        is_syntactically_valid = await connection.validate_query(draft_query)
        
        if not is_syntactically_valid:
            # Query has syntax errors
            warning_event = {
                "type": "agent:warning",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "Query validation failed - syntax errors detected",
                    "content": "⚠️ SQL query has syntax errors",
                    "progress": 30
                }
            }
            
            logging.warning(f"[VALIDATE_DRAFT_QUERY] Draft query syntactic validation failed")
            
            tool_message = ToolMessage(
                content="⚠️ Query validation failed - syntax errors",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, syntax_progress_event, warning_event],
                    "validation_attempts": attempt,
                    "query_validation_error": "Query syntax validation failed",
                    "validation_type": "syntactic"
                }
            )

        # STEP 2: Semantic validation using model
        semantic_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Validating query semantics and data patterns...",
                "content": "🧠 Checking if query matches actual data patterns",
                "progress": 60
            }
        }

        # Get context for semantic validation
        comprehensive_context = state.get("comprehensive_context", {})
        query_plan = comprehensive_context.get("query_plan", {})
        table_examples = comprehensive_context.get("table_examples", {})
        user_question = comprehensive_context.get("user_question", "")

        # Create semantic validation prompt
        semantic_validation_prompt = f"""
You are an expert database analyst. Analyze the following SQL query to determine if it will return meaningful results based on the actual data patterns in the database.

USER QUESTION: {user_question}

GENERATED SQL QUERY:
{draft_query}

QUERY PLAN CONTEXT:
{json.dumps(query_plan, indent=2) if query_plan else "No query plan available"}

ACTUAL DATA SAMPLES:
{json.dumps(table_examples, indent=2) if table_examples else "No sample data available"}

SEMANTIC VALIDATION TASKS:
1. Check if column names in WHERE clauses exist and are spelled correctly
2. Verify that filter values match the actual data formats in the samples
3. Ensure date/time formats match what's actually stored
4. Check if string values use the correct case and format
5. Validate that numeric ranges are reasonable based on sample data
6. Confirm that the query strategy aligns with the user's question

CRITICAL ANALYSIS AREAS:
- Do the WHERE clause values match the actual data formats shown in samples?
- Are timezone/date formats consistent with sample data?
- Do string filters use the exact format found in the data?
- Are column references correct and exist in the schema?
- Will this query likely return results based on the sample data?

Respond with a JSON object:
{{
    "is_semantically_valid": true|false,
    "confidence_score": 0.9,
    "validation_issues": [
        {{
            "issue_type": "format_mismatch|column_error|value_error|logic_error",
            "column": "column_name",
            "current_value": "value_in_query",
            "expected_value": "correct_value_from_samples",
            "description": "detailed explanation of the issue",
            "severity": "high|medium|low"
        }}
    ],
    "likely_to_return_results": true|false,
    "reasoning": "explanation of why the query will or won't work",
    "suggested_corrections": [
        {{
            "original": "incorrect_part",
            "corrected": "correct_part",
            "reason": "why this correction is needed"
        }}
    ]
}}

IMPORTANT: Base your analysis on the ACTUAL data samples provided. Look for exact format matches.
"""

        # Get semantic validation from model
        semantic_response = await handler.model.ainvoke(semantic_validation_prompt)
        
        try:
            semantic_validation = json.loads(semantic_response.content)
            
            is_semantically_valid = semantic_validation.get("is_semantically_valid", False)
            confidence_score = semantic_validation.get("confidence_score", 0.0)
            validation_issues = semantic_validation.get("validation_issues", [])
            likely_to_return_results = semantic_validation.get("likely_to_return_results", False)
            reasoning = semantic_validation.get("reasoning", "")
            suggested_corrections = semantic_validation.get("suggested_corrections", [])

            # Determine overall validation result
            if is_semantically_valid and confidence_score > 0.7:
                # Query is both syntactically and semantically valid
                success_event = {
                    "type": "agent:progress",
                    "name": "QueryGeneration",
                    "data": {
                        "scope": "QueryGeneration",
                        "description": f"Query validation successful (confidence: {confidence_score:.1f})",
                        "content": f"✅ Query Validation Successful\n\n**Validated SQL Query:**\n```sql\n{draft_query}\n```\n\n**Validation Results:**\n- Syntax: ✅ Valid\n- Semantics: ✅ Valid (confidence: {confidence_score:.1f})\n- Likely to return results: {'✅ Yes' if likely_to_return_results else '⚠️ Uncertain'}\n\n**AI Reasoning:** {reasoning}",
                        "progress": 100
                    }
                }
                
                logging.info(f"[VALIDATE_DRAFT_QUERY] Draft query validation successful (confidence: {confidence_score:.1f})")
            
                tool_message = ToolMessage(
                    content=f"✅ Query validation successful (confidence: {confidence_score:.1f})",
                    tool_call_id=tool_call_id
                )
                return Command(update={
                            "messages": [tool_message],
                            "agent_lifecycle_events": [start_progress_event, syntax_progress_event, semantic_progress_event, success_event],
                "validated_query": draft_query,
                            "sql_query": draft_query,  # Also set sql_query since validation passed
                            "validation_attempts": attempt,
                            "workflow_stage": "validate",
                            "semantic_validation": semantic_validation
            })
            else:
                # Query has semantic issues
                warning_event = {
                    "type": "agent:warning",
                    "name": "QueryGeneration",
                    "data": {
                        "scope": "QueryGeneration",
                        "description": f"Query semantic validation failed (confidence: {confidence_score:.1f})",
                        "content": f"⚠️ Query Validation Issues Detected\n\n**Query Being Validated:**\n```sql\n{draft_query}\n```\n\n**Validation Results:**\n- Syntax: ✅ Valid\n- Semantics: ❌ Issues Found (confidence: {confidence_score:.1f})\n- Likely to return results: {'❌ No' if not likely_to_return_results else '⚠️ Uncertain'}\n\n**AI Reasoning:** {reasoning}\n\n**Issues Found:**\n" + "\n".join([f"- {issue.get('description', 'Unknown issue')} (Severity: {issue.get('severity', 'unknown')})" for issue in validation_issues[:3]]) + (f"\n\n**Suggested Corrections:**\n" + "\n".join([f"- {correction.get('original', '')} → {correction.get('corrected', '')} ({correction.get('reason', '')})" for correction in suggested_corrections[:3]]) if suggested_corrections else ""),
                        "progress": 60
                    }
                }
                
                logging.warning(f"[VALIDATE_DRAFT_QUERY] Draft query semantic validation failed (confidence: {confidence_score:.1f})")
                
                # Format validation issues for error message
                issues_summary = []
                for issue in validation_issues[:3]:  # Show first 3 issues
                    issues_summary.append(f"- {issue.get('description', 'Unknown issue')}")
                
                tool_message = ToolMessage(
                    content=f"⚠️ Query semantic validation failed (confidence: {confidence_score:.1f})\nIssues:\n" + "\n".join(issues_summary),
                    tool_call_id=tool_call_id
                )
                
                return Command(
                    update={
                        "messages": [tool_message],
                        "agent_lifecycle_events": [start_progress_event, syntax_progress_event, semantic_progress_event, warning_event],
                        "validation_attempts": attempt,
                        "query_validation_error": f"Semantic validation failed: {reasoning}",
                        "validation_type": "semantic",
                        "semantic_validation": semantic_validation,
                        "validation_issues": validation_issues,
                        "suggested_corrections": suggested_corrections
                    }
                )

        except json.JSONDecodeError as e:
            logging.error(f"[VALIDATE_DRAFT_QUERY] Failed to parse semantic validation response: {e}")
            
            # Fall back to syntactic validation only
            success_event = {
                "type": "agent:progress",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "Syntactic validation successful (semantic validation failed)",
                    "content": "✅ SQL query syntax is valid (semantic check failed)",
                    "progress": 100
                }
            }
            
            tool_message = ToolMessage(
                content="✅ Query syntactic validation successful (semantic validation failed)",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, syntax_progress_event, semantic_progress_event, success_event],
                    "validated_query": draft_query,
                    "sql_query": draft_query,  # Also set sql_query since syntactic validation passed
                    "validation_attempts": attempt,
                    "workflow_stage": "validate",
                    "semantic_validation_error": "Failed to parse semantic validation response"
                }
            )
            
    except Exception as e:
        logging.error(f"[VALIDATE_DRAFT_QUERY] Validation error: {e}")
        
        error_event = {
            "type": "agent:error",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Query validation error: {str(e)}",
                "content": "❌ Validation failed with error",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Query validation failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "query_validation_error": str(e),
                "error": {"type": "validation_error", "message": str(e)}
            }
        )


@tool
async def correct_draft_query(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    validation_error: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Correct the draft query based on validation errors and semantic analysis."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Starting query correction process...",
                "content": "🔧 Correcting query based on validation feedback",
                "progress": 10
            }
        }
    
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for query correction",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ Model handler not available",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "handler_error", "message": "Model handler not available"}
                }
            )
        
        draft_query = state.get("draft_query")
        if not draft_query:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "No draft query available to correct",
                    "content": "❌ Missing draft query for correction",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ No draft query available to correct",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "query_error", "message": "No draft query available to correct"}
                }
            )
        
        # Increment correction attempts
        attempt = state.get("correction_attempts", 0) + 1
        
        # Emit analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Analyzing validation feedback (attempt {attempt})...",
                "content": "📊 Processing validation errors and suggested corrections",
                "progress": 30
            }
        }
        
        logging.info(f"[CORRECT_DRAFT_QUERY] Correcting draft query (attempt {attempt})")
        
        # Get validation context
        comprehensive_context = state.get("comprehensive_context", {})
        semantic_validation = state.get("semantic_validation", {})
        validation_issues = state.get("validation_issues", [])
        suggested_corrections = state.get("suggested_corrections", [])
        validation_type = state.get("validation_type", "unknown")
        
        # Build comprehensive correction prompt
        correction_prompt = f"""
You are an expert SQL query corrector. Fix the following SQL query based on the validation errors and semantic analysis.

ORIGINAL QUERY:
{draft_query}

VALIDATION ERROR:
{validation_error}

VALIDATION TYPE: {validation_type}

USER QUESTION: {comprehensive_context.get('user_question', '')}

SEMANTIC VALIDATION RESULTS:
{json.dumps(semantic_validation, indent=2) if semantic_validation else "No semantic validation available"}

SPECIFIC VALIDATION ISSUES:
{json.dumps(validation_issues, indent=2) if validation_issues else "No specific issues identified"}

SUGGESTED CORRECTIONS:
{json.dumps(suggested_corrections, indent=2) if suggested_corrections else "No suggested corrections available"}

ACTUAL DATA SAMPLES:
{json.dumps(comprehensive_context.get('table_examples', {}), indent=2)}

CORRECTION REQUIREMENTS:
1. Fix any syntax errors if this is a syntactic validation failure
2. Correct value formats to match actual data patterns from samples
3. Ensure column names are exact matches from the schema
4. Fix date/time formats to match the actual data
5. Correct string values to use exact case and format from samples
6. Maintain the original query intent and strategy

CRITICAL ANALYSIS:
- Look at the actual data samples to understand the correct formats
- Pay special attention to timezone formats, date formats, and string values
- Ensure all WHERE clause values match the patterns in the sample data
- Keep the query logic intact while fixing the format issues

Generate ONLY the corrected SQL query, no explanations or markdown formatting.
"""
        
        # Emit correction progress
        correction_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Generating corrected query using AI model...",
                "content": "🤖 Applying corrections based on validation feedback",
                "progress": 60
            }
        }
        
        # Get corrected query from model
        response = await handler.model.ainvoke(correction_prompt)
        corrected_query = response.content.strip()
        
        # Emit processing progress
        processing_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Processing and cleaning corrected query...",
                "content": "⚙️ Finalizing corrected SQL query",
                "progress": 80
            }
        }
        
        # Clean up the query (remove markdown formatting)
        if corrected_query.startswith("```sql"):
            corrected_query = corrected_query[6:]
        if corrected_query.endswith("```"):
            corrected_query = corrected_query[:-3]
        corrected_query = corrected_query.strip()
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Query correction complete (attempt {attempt})",
                "content": f"✅ Query Correction Applied\n\n**Original Query (with issues):**\n```sql\n{draft_query}\n```\n\n**Corrected Query:**\n```sql\n{corrected_query}\n```\n\n**Validation Error:** {validation_error}\n\n**Correction Applied:** Query has been updated to address validation issues and should now execute successfully.",
                "progress": 100
            }
        }
        
        logging.info(f"[CORRECT_DRAFT_QUERY] Generated corrected query (attempt {attempt}): {corrected_query[:100]}...")
        
        tool_message = ToolMessage(
            content=f"✅ Generated corrected query (attempt {attempt})",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, analysis_progress_event, correction_progress_event, processing_progress_event, completion_progress_event],
                "draft_query": corrected_query,  # Replace the draft query with corrected version
                "validated_query": corrected_query,  # Also set as validated since it was corrected based on validation feedback
                "correction_attempts": attempt,
                "workflow_stage": "correction",
                "previous_query": draft_query,  # Keep track of the original
                "correction_applied": True
            }
        )
        
    except Exception as e:
        logging.error(f"[CORRECT_DRAFT_QUERY] Error: {e}")
        
        error_event = {
            "type": "agent:error",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Query correction failed: {str(e)}",
                "content": "❌ Failed to correct query",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Failed to correct query: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "correction_error", "message": str(e)}
            }
        )


@tool
async def execute_validated_query(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Execute the validated query and handle zero-result cases intelligently."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Starting query execution...",
                "content": "🚀 Executing validated SQL query",
                "progress": 10
            }
        }
    
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection")
        
        if not connection:
                error_event = {
                    "type": "agent:error",
                    "name": "QueryGeneration",
                    "data": {
                        "scope": "QueryGeneration",
                        "description": "Database connection not available",
                        "content": "❌ No database connection for execution",
                        "progress": 0
                    }
                }
                
                tool_message = ToolMessage(
                    content="❌ Database connection not available",
                    tool_call_id=tool_call_id
                )
                
                return Command(
                    update={
                        "messages": [tool_message],
                        "agent_lifecycle_events": [start_progress_event, error_event],
                        "error": {"type": "connection_error", "message": "Database connection not available"}
                    }
                )
        
        validated_query = state.get("validated_query")
        if not validated_query:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "No validated query available to execute",
                    "content": "❌ Missing validated query for execution",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ No validated query available to execute",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, error_event],
                    "error": {"type": "query_error", "message": "No validated query available to execute"}
                }
            )
        
        # Increment execution attempts
        attempt = state.get("execution_attempts", 0) + 1
        
        # Emit execution progress
        execution_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Executing query against database (attempt {attempt})...",
                "content": f"⚡ Running query: {validated_query[:40]}...",
                "progress": 50
            }
        }
        
        logging.info(f"[EXECUTE_VALIDATED_QUERY] Executing validated query (attempt {attempt}): {validated_query[:100]}...")
        
        # Execute the query
        rows = connection.query(validated_query)
        
        # Emit processing progress
        processing_progress_event = {
            "type": "agent:progress",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": "Processing query results...",
                "content": "⚙️ Converting results to structured format",
                "progress": 80
            }
        }
        
        if rows is not None:
            # Convert SQLAlchemy rows to dictionaries
            results_data = convert_sqlalchemy_rows_to_dict(rows)
            row_count = len(results_data)
            
            logging.info(f"[EXECUTE_VALIDATED_QUERY] Query executed successfully, {row_count} rows returned")
            
            # Check for zero results and decide if we should regenerate
            if row_count == 0:
                zero_attempts = state.get("zero_result_attempts", 0) + 1
                should_regenerate = zero_attempts < 2  # Allow up to 2 regenerations
                
                zero_result_event = {
                    "type": "agent:warning",
                    "name": "QueryGeneration",
                    "data": {
                        "scope": "QueryGeneration",
                        "description": f"Query returned 0 rows (attempt {zero_attempts})",
                        "content": f"⚠️ Query Execution - No Results Found\n\n**Executed Query:**\n```sql\n{validated_query}\n```\n\n**Results:** 0 rows returned\n**Attempt:** {zero_attempts}/2\n**Status:** {'Will regenerate with adjustments' if should_regenerate else 'Maximum attempts reached'}\n\n**Analysis:** The query executed successfully but returned no data. This could indicate:\n- Filter conditions are too restrictive\n- Date/time formats don't match actual data\n- Column values don't exist in the expected format\n- Data may not exist for the specified criteria",
                        "progress": 90
                    }
                }
                
                logging.warning(f"[EXECUTE_VALIDATED_QUERY] Query returned 0 rows (attempt {zero_attempts}), should regenerate: {should_regenerate}")
                
                tool_message = ToolMessage(
                    content=f"⚠️ Query returned 0 rows (attempt {zero_attempts})",
                    tool_call_id=tool_call_id
                )
                
                return Command(
                    update={
                        "messages": [tool_message],
                        "agent_lifecycle_events": [start_progress_event, execution_progress_event, processing_progress_event, zero_result_event],
                        "execution_results": [],
                        "execution_attempts": attempt,
                        "zero_result_attempts": zero_attempts,
                        "workflow_stage": "execute"
                    }
                )
            else:
                # Success with data
                # Create a preview of the results for the event
                preview_data = ""
                if results_data:
                    # Show column names
                    columns = list(results_data[0].keys()) if results_data[0] else []
                    preview_data += f"**Columns:** {', '.join(columns)}\n\n"
                    
                    # Show first few rows as a preview
                    preview_data += "**Sample Results:**\n"
                    for i, row in enumerate(results_data[:3]):  # Show first 3 rows
                        preview_data += f"Row {i+1}: {dict(row)}\n"
                    
                    if row_count > 3:
                        preview_data += f"... and {row_count - 3} more rows"
                
                success_event = {
                    "type": "agent:progress",
                    "name": "QueryGeneration",
                    "data": {
                        "scope": "QueryGeneration",
                        "description": f"Query executed successfully - {row_count} rows returned",
                        "content": f"✅ Query Execution Successful\n\n**Executed Query:**\n```sql\n{validated_query}\n```\n\n**Results:** {row_count} rows returned\n\n{preview_data}",
                        "progress": 100
                    }
                }
                
                tool_message = ToolMessage(
                    content=f"✅ Query executed successfully - {row_count} rows returned",
                    tool_call_id=tool_call_id
                )
                
                return Command(
                    update={
                        "messages": [tool_message],
                        "agent_lifecycle_events": [start_progress_event, execution_progress_event, processing_progress_event, success_event],
                        "execution_results": results_data,
                        "sql_query": validated_query,
                        "execution_attempts": attempt,
                        "workflow_stage": "complete",
                        "workflow_completed": True
                    }
                )
        else:
            error_event = {
                "type": "agent:error",
                "name": "QueryGeneration",
                "data": {
                    "scope": "QueryGeneration",
                    "description": "Query execution returned no result",
                    "content": "❌ Query execution failed",
                    "progress": 0
                }
            }
            
            tool_message = ToolMessage(
                content="❌ Query execution returned no result",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, execution_progress_event, error_event],
                    "error": {"type": "execution_error", "message": "Query execution returned no result"}
                }
            )
            
    except Exception as e:
        logging.error(f"[EXECUTE_VALIDATED_QUERY] Query execution failed: {e}")
        
        error_event = {
            "type": "agent:error",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Query execution failed: {str(e)}",
                "content": "❌ Database execution error",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Query execution failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "execution_error", "message": str(e)}
            }
        )


@tool
async def get_table_sample_data(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    table_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    sample_size: int = 5
) -> Command:
    """Get sample data from a specific table to understand data formats."""
    # This delegates to the main implementation in data_analysis.py
    from doorbeen.core.assistants.analysis.sql.tools.data_analysis import get_table_sample_data as get_sample
    return await get_sample(config, state, table_name, tool_call_id, sample_size)


@tool
async def notify_outputs(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Notify about the outputs and accomplishments of the query generation agent."""
    
    try:
        # Extract relevant information from state
        workflow_stage = state.get("workflow_stage", "unknown")
        sql_query = state.get("sql_query")
        execution_results = state.get("execution_results", [])
        row_count = len(execution_results)
        
        # Build contextual content
        content_parts = ["🎯 Query Generation Workflow Complete"]
        
        # Add workflow stage info
        content_parts.append(f"\n**Workflow Stage:** {workflow_stage}")
        
        # Add final query if available
        if sql_query:
            content_parts.append(f"\n**Final SQL Query:**\n```sql\n{sql_query}\n```")
        
        # Add execution results summary
        if execution_results:
            content_parts.append(f"\n**Execution Results:** {row_count} rows returned")
            
            # Show column names from first result
            if execution_results and row_count > 0:
                sample_keys = list(execution_results[0].keys()) if execution_results[0] else []
                content_parts.append(f"**Columns:** {', '.join(sample_keys)}")
                
                # Show a sample result
                if execution_results[0]:
                    content_parts.append(f"**Sample Row:** {dict(execution_results[0])}")
        else:
            content_parts.append(f"\n**Execution Results:** No data returned")
        
        # Add attempt information
        generation_attempts = state.get("generation_attempts", 0)
        validation_attempts = state.get("validation_attempts", 0)
        execution_attempts = state.get("execution_attempts", 0)
        zero_attempts = state.get("zero_result_attempts", 0)
        
        content_parts.append(f"\n**Attempts:** Generation: {generation_attempts}, Validation: {validation_attempts}, Execution: {execution_attempts}")
        if zero_attempts > 0:
            content_parts.append(f"**Zero Results:** {zero_attempts} attempts returned no data")
        
        # Create the notification event
        notification_event = {
            "type": "agent:end",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Query generation workflow completed at stage: {workflow_stage}",
                "content": "\n".join(content_parts)
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Query generation outputs notified",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [notification_event]
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "QueryGeneration",
            "data": {
                "scope": "QueryGeneration",
                "description": f"Output notification failed: {str(e)}",
                "content": f"❌ Failed to notify outputs: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Output notification failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event]
            }
        )


def query_generation_pre_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Pre-model hook for query generation agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "QueryGeneration",
        "data": {
            "scope": "QueryGeneration",
            "description": "Starting intelligent SQL query generation with draft-validate-execute workflow",
            "content": "⚡ Starting enhanced query generation with zero-result intelligence"
        }
    }
    return {"agent_lifecycle_events": [event]}


def query_generation_post_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Post-model hook for query generation agent - emits agent end event with detailed information"""
    workflow_stage = state.get("workflow_stage", "unknown")
    sql_query = state.get("sql_query")
    execution_results = state.get("execution_results", [])
    row_count = len(execution_results)
    
    # Create detailed content for the event
    content_parts = ["🎯 Query Generation Workflow Complete"]
    
    # Add workflow stage info
    content_parts.append(f"\n**Workflow Stage:** {workflow_stage}")
    
    # Add final query if available
    if sql_query:
        content_parts.append(f"\n**Final SQL Query:**\n```sql\n{sql_query}\n```")
    
    # Add execution results summary
    if execution_results:
        content_parts.append(f"\n**Execution Results:** {row_count} rows returned")
        
        # Show column names from first result
        if execution_results and row_count > 0:
            sample_keys = list(execution_results[0].keys()) if execution_results[0] else []
            content_parts.append(f"**Columns:** {', '.join(sample_keys)}")
            
            # Show a sample result
            if execution_results[0]:
                content_parts.append(f"**Sample Row:** {dict(execution_results[0])}")
    else:
        content_parts.append(f"\n**Execution Results:** No data returned")
    
    # Add attempt information
    generation_attempts = state.get("generation_attempts", 0)
    validation_attempts = state.get("validation_attempts", 0)
    execution_attempts = state.get("execution_attempts", 0)
    zero_attempts = state.get("zero_result_attempts", 0)
    
    content_parts.append(f"\n**Attempts:** Generation: {generation_attempts}, Validation: {validation_attempts}, Execution: {execution_attempts}")
    if zero_attempts > 0:
        content_parts.append(f"**Zero Results:** {zero_attempts} attempts returned no data")
    
    event = {
        "type": "agent:end",
        "name": "QueryGeneration",
        "data": {
            "scope": "QueryGeneration",
            "description": f"Query generation workflow completed at stage: {workflow_stage}",
            "content": "\n".join(content_parts)
        }
    }
    
    # Log detailed information for debugging
    import logging
    logging.info(f"[QUERY_GENERATION_POST_HOOK] Workflow completed:")
    logging.info(f"  - Stage: {workflow_stage}")
    logging.info(f"  - Query: {sql_query}")
    logging.info(f"  - Results: {row_count} rows")
    if execution_results and row_count > 0:
        logging.info(f"  - Sample result: {execution_results[0]}")
    
    return {"agent_lifecycle_events": [event]} 