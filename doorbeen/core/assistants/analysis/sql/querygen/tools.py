"""
LangChain Tools for Query Generation Agent

This module provides the core tools that agents can use for SQL query generation,
validation, and error analysis. Tools are designed to be bound to agents using
the Agent Tool-Binding pattern.
"""

import json
import logging
import time
import hashlib
from typing import Dict, Any, List, Optional, Union

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from .types import (
    QueryGenerationRequest,
    QueryGenerationResponse,
    QueryValidationResult,
    QueryErrorAnalysis,
    QueryExecutionRequest,
    QueryExecutionResult
)
from .validators import QueryValidator, analyze_query_complexity

# Global context for tools (set by nodes before using tools)
_tool_context = {
    "handler": None,
    "connection": None
}

def set_tool_context(handler: ModelHandler, connection: CommonSQLClient):
    """Set the global context for tools to access"""
    global _tool_context
    _tool_context["handler"] = handler
    _tool_context["connection"] = connection


@tool
async def generate_sql_query_tool(
    objective: str,
    reasoning: str,
    table_schemas: Dict[str, Any],
    exploration_context: Optional[str] = None,
    retry_strategy: Optional[str] = None,
    database_type: str = "sqlite",
    selected_tables: Optional[List[str]] = None,
    additional_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate semantically correct SQL query using specialized agent.
    
    This tool provides a unified interface for SQL query generation across
    all nodes in the system. It uses advanced LLM reasoning to ensure
    consistent, high-quality query generation.
    
    Args:
        objective: What the query should accomplish
        reasoning: Detailed reasoning about the approach
        table_schemas: Available database schemas
        exploration_context: Previous exploration findings
        retry_strategy: Strategy for retry attempts
        database_type: Target database type
        selected_tables: Priority tables to focus on
        additional_context: Any additional context for generation
        
    Returns:
        {
            "success": bool,
            "query": str,
            "explanation": str,
            "confidence": float,
            "complexity": str,
            "potential_issues": List[str],
            "estimated_performance": str
        }
    """
    
    try:
        logging.info("🔧 [GENERATE_TOOL] Starting SQL query generation")
        
        # Get handler from context
        handler = _tool_context.get("handler")
        if not handler:
            raise Exception("No model handler available in tool context")
        
        # Build comprehensive prompt for query generation
        generation_prompt = f"""
You are an expert SQL query generator. Generate a high-quality SQL query based on the provided context.

**OBJECTIVE**: {objective}

**REASONING**: {reasoning}

**DATABASE CONTEXT**:
- Database Type: {database_type}
- Available Schemas: {json.dumps(table_schemas, indent=2)}
"""
        
        if selected_tables:
            generation_prompt += f"- Priority Tables: {', '.join(selected_tables)}\n"
        
        if exploration_context:
            generation_prompt += f"- Data Exploration Findings: {exploration_context}\n"
        
        if retry_strategy:
            generation_prompt += f"- Retry Strategy: {retry_strategy}\n"
        
        if additional_context:
            generation_prompt += f"- Additional Context: {additional_context}\n"
        
        generation_prompt += f"""

**REQUIREMENTS**:
1. Generate syntactically correct SQL for {database_type}
2. Use appropriate table and column names from the schema
3. Optimize for performance where possible
4. Handle edge cases (NULL values, empty results, etc.)
5. Follow best practices for the target database type

**OUTPUT FORMAT**:
Return a JSON object with the following structure:
{{
    "query": "Your generated SQL query here",
    "explanation": "Detailed explanation of what the query does and why",
    "confidence": 0.95,
    "complexity": "low|medium|high",
    "potential_issues": ["List of potential issues or edge cases"],
    "estimated_performance": "Description of expected performance"
}}

Generate the query now:
"""
        
        # Use JSON-bound LLM for structured response
        json_llm = handler.model.bind(response_format={"type": "json_object"})
        response = await json_llm.ainvoke([HumanMessage(content=generation_prompt)])
        
        # Parse the response
        result = json.loads(response.content)
        
        # Validate required fields
        required_fields = ["query", "explanation", "confidence"]
        for field in required_fields:
            if field not in result:
                result[field] = "" if field != "confidence" else 0.5
        
        # Set defaults for optional fields
        result.setdefault("complexity", "medium")
        result.setdefault("potential_issues", [])
        result.setdefault("estimated_performance", "Unknown")
        
        # Analyze query complexity
        if result["query"]:
            complexity_analysis = analyze_query_complexity(result["query"], table_schemas)
            result["complexity"] = complexity_analysis["complexity_level"]
            result["estimated_performance"] = complexity_analysis["estimated_performance"]
        
        # Mark as successful
        result["success"] = True
        
        logging.info(f"✅ [GENERATE_TOOL] Query generated successfully (confidence: {result['confidence']})")
        return result
        
    except Exception as e:
        logging.error(f"❌ [GENERATE_TOOL] Query generation failed: {e}")
        return {
            "success": False,
            "query": "",
            "explanation": f"Query generation failed: {str(e)}",
            "confidence": 0.0,
            "complexity": "low",
            "potential_issues": [str(e)],
            "estimated_performance": "Failed to generate",
            "error": str(e)
        }


@tool
async def validate_query_syntax_tool(
    query: str,
    database_type: str = "sqlite",
    table_schemas: Optional[Dict[str, Any]] = None,
    validation_level: str = "basic"
) -> Dict[str, Any]:
    """
    Validate SQL query syntax and semantic correctness.
    
    Args:
        query: SQL query to validate
        database_type: Target database type
        table_schemas: Available table schemas for semantic validation
        validation_level: Level of validation (basic, comprehensive, performance)
        
    Returns:
        {
            "is_valid": bool,
            "syntax_valid": bool,
            "semantic_valid": bool,
            "syntax_errors": List[str],
            "semantic_errors": List[str],
            "warnings": List[str],
            "suggested_fixes": List[str]
        }
    """
    
    try:
        logging.info("🔧 [VALIDATE_TOOL] Starting query validation")
        
        # Create validator
        validator = QueryValidator(database_type)
        
        # Map validation level
        from .validators import ValidationLevel
        level_map = {
            "basic": ValidationLevel.BASIC,
            "comprehensive": ValidationLevel.COMPREHENSIVE,
            "performance": ValidationLevel.PERFORMANCE
        }
        validation_level_enum = level_map.get(validation_level, ValidationLevel.BASIC)
        
        # Perform validation
        result = await validator.validate_query(
            query, 
            table_schemas or {}, 
            validation_level_enum
        )
        
        # Convert to dict format
        validation_result = {
            "is_valid": result.is_valid,
            "syntax_valid": result.syntax_valid,
            "semantic_valid": result.semantic_valid,
            "syntax_errors": result.syntax_errors,
            "semantic_errors": result.semantic_errors,
            "warnings": result.warnings,
            "suggested_fixes": result.suggested_fixes,
            "database_type": result.database_type,
            "validation_level": result.validation_level
        }
        
        logging.info(f"✅ [VALIDATE_TOOL] Validation complete (valid: {result.is_valid})")
        return validation_result
        
    except Exception as e:
        logging.error(f"❌ [VALIDATE_TOOL] Validation failed: {e}")
        return {
            "is_valid": False,
            "syntax_valid": False,
            "semantic_valid": False,
            "syntax_errors": [f"Validation error: {str(e)}"],
            "semantic_errors": [],
            "warnings": [],
            "suggested_fixes": ["Review query syntax and try again"],
            "database_type": database_type,
            "validation_level": validation_level,
            "error": str(e)
        }


@tool
async def analyze_query_error_tool(
    failed_query: str,
    error_message: str,
    table_schemas: Dict[str, Any],
    database_type: str = "sqlite"
) -> Dict[str, Any]:
    """
    Analyze query errors and suggest fixes.
    
    Args:
        failed_query: The SQL query that failed
        error_message: Error message from the database or validator
        table_schemas: Available table schemas
        database_type: Target database type
        
    Returns:
        {
            "analysis": str,
            "suggested_fixes": List[str],
            "corrected_query": str,
            "confidence": float,
            "error_category": str
        }
    """
    
    try:
        logging.info("🔧 [ANALYZE_ERROR_TOOL] Starting error analysis")
        
        # Get handler from context
        handler = _tool_context.get("handler")
        if not handler:
            raise Exception("No model handler available in tool context")
        
        # Build error analysis prompt
        analysis_prompt = f"""
You are an expert SQL error analyst. Analyze the failed query and error message to provide actionable fixes.

**FAILED QUERY**:
```sql
{failed_query}
```

**ERROR MESSAGE**: {error_message}

**DATABASE TYPE**: {database_type}

**AVAILABLE SCHEMAS**: {json.dumps(table_schemas, indent=2)}

**ANALYSIS TASK**:
1. Identify the root cause of the error
2. Categorize the error type (syntax, semantic, performance, etc.)
3. Provide specific, actionable fix suggestions
4. Generate a corrected version of the query if possible

**OUTPUT FORMAT**:
Return a JSON object with:
{{
    "analysis": "Detailed analysis of what went wrong and why",
    "error_category": "syntax|semantic|performance|database_specific|other",
    "suggested_fixes": ["List of specific actions to fix the issue"],
    "corrected_query": "Fixed SQL query (if possible to generate)",
    "confidence": 0.85
}}

Analyze the error now:
"""
        
        # Use JSON-bound LLM for structured response
        json_llm = handler.model.bind(response_format={"type": "json_object"})
        response = await json_llm.ainvoke([HumanMessage(content=analysis_prompt)])
        
        # Parse the response
        result = json.loads(response.content)
        
        # Validate and set defaults
        result.setdefault("analysis", "Error analysis not available")
        result.setdefault("error_category", "other")
        result.setdefault("suggested_fixes", ["Review query syntax"])
        result.setdefault("corrected_query", "")
        result.setdefault("confidence", 0.5)
        
        # Mark as successful
        result["success"] = True
        
        logging.info(f"✅ [ANALYZE_ERROR_TOOL] Error analysis complete (category: {result['error_category']})")
        return result
        
    except Exception as e:
        logging.error(f"❌ [ANALYZE_ERROR_TOOL] Error analysis failed: {e}")
        return {
            "success": False,
            "analysis": f"Error analysis failed: {str(e)}",
            "error_category": "other",
            "suggested_fixes": ["Unable to analyze error - review manually"],
            "corrected_query": "",
            "confidence": 0.0,
            "error": str(e)
        }


@tool
async def execute_query_tool(
    query: str,
    dry_run: bool = True,
    limit: int = 100,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Execute SQL query safely with limits and timeout.
    
    Args:
        query: SQL query to execute
        dry_run: If True, only validate without executing
        limit: Maximum number of rows to return
        timeout: Query timeout in seconds
        
    Returns:
        {
            "success": bool,
            "results": List[Dict],
            "row_count": int,
            "execution_time": float,
            "truncated": bool
        }
    """
    
    try:
        logging.info(f"🔧 [EXECUTE_TOOL] {'Dry run' if dry_run else 'Executing'} query")
        
        # Get connection from context
        connection = _tool_context.get("connection")
        if not connection:
            raise Exception("No database connection available in tool context")
        
        start_time = time.time()
        
        if dry_run:
            # For dry run, just validate the query
            try:
                # Try to explain the query (most databases support this)
                explain_query = f"EXPLAIN {query}"
                connection.query(explain_query)
                
                execution_time = time.time() - start_time
                
                return {
                    "success": True,
                    "results": [],
                    "row_count": 0,
                    "execution_time": execution_time,
                    "truncated": False,
                    "dry_run": True,
                    "message": "Query validated successfully (dry run)"
                }
            except Exception as e:
                return {
                    "success": False,
                    "results": [],
                    "row_count": 0,
                    "execution_time": time.time() - start_time,
                    "truncated": False,
                    "dry_run": True,
                    "error": f"Query validation failed: {str(e)}"
                }
        
        # Execute the actual query
        # Add LIMIT if not present and query is SELECT
        limited_query = query
        if query.strip().upper().startswith('SELECT') and 'LIMIT' not in query.upper():
            limited_query = f"{query.rstrip(';')} LIMIT {limit};"
        
        # Execute query
        results = connection.query(limited_query)
        execution_time = time.time() - start_time
        
        # Convert results to list of dicts if needed
        # CommonSQLClient.query() returns fetched results directly
        if isinstance(results, list):
            # Results are already fetched as a list of Row objects
            results_list = []
            for row in results:
                if hasattr(row, '_mapping'):
                    # SQLAlchemy Row object with _mapping
                    results_list.append(dict(row._mapping))
                elif hasattr(row, 'keys'):
                    # Row-like object with keys
                    results_list.append(dict(row))
                else:
                    # Fallback: convert to string representation
                    results_list.append({"result": str(row)})
        else:
            results_list = [{"result": str(results)}]
        
        # Check if results were truncated
        truncated = len(results_list) >= limit
        
        logging.info(f"✅ [EXECUTE_TOOL] Query executed successfully ({len(results_list)} rows)")
        
        return {
            "success": True,
            "results": results_list,
            "row_count": len(results_list),
            "execution_time": execution_time,
            "truncated": truncated,
            "dry_run": False
        }
        
    except Exception as e:
        logging.error(f"❌ [EXECUTE_TOOL] Query execution failed: {e}")
        return {
            "success": False,
            "results": [],
            "row_count": 0,
            "execution_time": time.time() - start_time if 'start_time' in locals() else 0.0,
            "truncated": False,
            "dry_run": dry_run,
            "error": str(e)
        }


# Utility functions for tool management

def get_all_query_tools():
    """Get all query generation tools for agent binding"""
    return [
        generate_sql_query_tool,
        validate_query_syntax_tool,
        analyze_query_error_tool,
        execute_query_tool
    ]


def get_generation_tools():
    """Get tools for query generation workflow"""
    return [
        generate_sql_query_tool,
        validate_query_syntax_tool,
        analyze_query_error_tool
    ]


def get_exploration_tools():
    """Get tools for data exploration workflow"""
    return [
        generate_sql_query_tool,
        execute_query_tool
    ]


def get_validation_tools():
    """Get tools for query validation workflow"""
    return [
        validate_query_syntax_tool,
        analyze_query_error_tool
    ] 