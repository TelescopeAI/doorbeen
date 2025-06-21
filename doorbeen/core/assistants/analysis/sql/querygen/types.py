"""
Type definitions for Query Generation Agent

This module contains all Pydantic models and type definitions used by the
Query Generation Agent and its tools.
"""

from typing import Dict, Any, List, Optional, Literal

from pydantic import Field

from doorbeen.core.types.ts_model import TSModel


class QueryGenerationRequest(TSModel):
    """Request model for SQL query generation"""
    
    objective: str = Field(description="What the query should accomplish")
    reasoning: str = Field(description="Detailed reasoning about the approach")
    table_schemas: Dict[str, Any] = Field(description="Available database schemas")
    exploration_context: Optional[str] = Field(default=None, description="Previous exploration findings")
    retry_strategy: Optional[str] = Field(default=None, description="Strategy for retry attempts")
    database_type: str = Field(default="sqlite", description="Target database type")
    selected_tables: Optional[List[str]] = Field(default=None, description="Pre-selected tables to focus on")
    additional_context: Optional[str] = Field(default=None, description="Additional context or constraints")


class QueryGenerationResponse(TSModel):
    """Response model for SQL query generation"""
    
    success: bool = Field(description="Whether query generation succeeded")
    query: str = Field(description="Generated SQL query")
    explanation: str = Field(description="Explanation of the query logic")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")
    complexity: Literal["low", "medium", "high"] = Field(description="Estimated query complexity")
    potential_issues: List[str] = Field(default_factory=list, description="Potential issues or warnings")
    retry_count: int = Field(default=0, description="Number of retry attempts made")
    error: Optional[str] = Field(default=None, description="Error message if generation failed")
    
    # Additional metadata
    estimated_rows: Optional[int] = Field(default=None, description="Estimated number of result rows")
    performance_notes: Optional[str] = Field(default=None, description="Performance considerations")
    alternative_approaches: List[str] = Field(default_factory=list, description="Alternative query approaches")


class QueryValidationResult(TSModel):
    """Result of query syntax and semantic validation"""
    
    is_valid: bool = Field(description="Whether the query is valid")
    syntax_valid: bool = Field(description="Whether syntax is correct")
    semantic_valid: bool = Field(description="Whether semantics are correct")
    
    # Error details
    syntax_errors: List[str] = Field(default_factory=list, description="Syntax error messages")
    semantic_errors: List[str] = Field(default_factory=list, description="Semantic error messages")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    # Validation metadata
    database_type: str = Field(description="Database type used for validation")
    validation_level: Literal["basic", "comprehensive"] = Field(default="basic", description="Level of validation performed")
    
    # Suggestions
    suggested_fixes: List[str] = Field(default_factory=list, description="Suggested fixes for issues")


class QueryErrorAnalysis(TSModel):
    """Analysis of query execution errors"""
    
    error_type: str = Field(description="Type of error (syntax, semantic, runtime, etc.)")
    error_message: str = Field(description="Original error message")
    root_cause: str = Field(description="Identified root cause of the error")
    
    # Fix suggestions
    suggested_fix: Optional[str] = Field(default=None, description="Suggested corrected query")
    fix_explanation: str = Field(description="Explanation of the fix")
    fix_confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the fix")
    
    # Context
    database_type: str = Field(description="Database type where error occurred")
    query_context: Optional[str] = Field(default=None, description="Context where query was used")
    
    # Alternative approaches
    alternative_queries: List[str] = Field(default_factory=list, description="Alternative query approaches")
    prevention_tips: List[str] = Field(default_factory=list, description="Tips to prevent similar errors")


class QueryExecutionRequest(TSModel):
    """Request model for query execution via tools"""
    
    query: str = Field(description="SQL query to execute")
    database_type: str = Field(description="Target database type")
    limit_rows: Optional[int] = Field(default=None, description="Limit number of returned rows")
    timeout_seconds: Optional[int] = Field(default=30, description="Query timeout in seconds")
    dry_run: bool = Field(default=False, description="Whether to perform a dry run (validate only)")


class QueryExecutionResult(TSModel):
    """Result of query execution"""
    
    success: bool = Field(description="Whether execution succeeded")
    result_data: Optional[List[Dict[str, Any]]] = Field(default=None, description="Query result data")
    row_count: int = Field(default=0, description="Number of rows returned")
    execution_time_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")
    
    # Error handling
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    error_type: Optional[str] = Field(default=None, description="Type of error")
    
    # Metadata
    columns: List[str] = Field(default_factory=list, description="Column names in result")
    query_hash: Optional[str] = Field(default=None, description="Hash of executed query for caching")
    
    # Performance metrics
    rows_examined: Optional[int] = Field(default=None, description="Number of rows examined")
    query_plan: Optional[str] = Field(default=None, description="Query execution plan if available")


class DataExplorationRequest(TSModel):
    """Request for data exploration queries"""
    
    exploration_type: Literal["schema", "sampling", "quality", "patterns"] = Field(description="Type of exploration")
    target_tables: List[str] = Field(description="Tables to explore")
    table_schemas: Dict[str, Any] = Field(description="Available table schemas")
    sample_size: Optional[int] = Field(default=100, description="Sample size for data sampling")
    focus_areas: List[str] = Field(default_factory=list, description="Specific areas to focus exploration on")


class DataExplorationResult(TSModel):
    """Result of data exploration"""
    
    exploration_type: str = Field(description="Type of exploration performed")
    findings: str = Field(description="Key findings from exploration")
    queries_executed: List[str] = Field(description="Queries that were executed")
    data_samples: Optional[List[Dict[str, Any]]] = Field(default=None, description="Sample data if applicable")
    
    # Insights
    data_quality_score: Optional[float] = Field(default=None, description="Overall data quality score (0-1)")
    temporal_range: Optional[Dict[str, Any]] = Field(default=None, description="Temporal data range information")
    volume_estimates: Optional[Dict[str, int]] = Field(default=None, description="Volume estimates per table")
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Recommendations based on exploration")
    potential_issues: List[str] = Field(default_factory=list, description="Potential data issues identified") 