"""
State management for Query Generation Agent

This module defines the context models used by the Query Generation Agent
to track the generation process, validation steps, and error handling.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel
from .types import (
    QueryGenerationRequest,
    QueryGenerationResponse,
    QueryValidationResult,
    QueryErrorAnalysis
)


class QueryGenerationState(TSModel):
    """State model for Query Generation Agent workflow"""
    
    # Input request
    request: QueryGenerationRequest = Field(description="Original query generation request")
    
    # Generation strategy
    generation_strategy: Literal["standard", "exploration", "retry", "fallback"] = Field(
        default="standard", 
        description="Strategy being used for query generation"
    )
    
    # Generation attempts
    generation_attempts: List[QueryGenerationResponse] = Field(
        default_factory=list, 
        description="History of generation attempts"
    )
    current_attempt: int = Field(default=0, description="Current attempt number")
    max_attempts: int = Field(default=3, description="Maximum generation attempts allowed")
    
    # Validation context
    last_validation: Optional[QueryValidationResult] = Field(
        default=None, 
        description="Result of last validation attempt"
    )
    validation_passed: bool = Field(default=False, description="Whether validation passed")
    
    # Error handling
    error_history: List[QueryErrorAnalysis] = Field(
        default_factory=list, 
        description="History of errors and their analyses"
    )
    last_error: Optional[str] = Field(default=None, description="Last error encountered")
    
    # Final result
    final_result: Optional[QueryGenerationResponse] = Field(
        default=None, 
        description="Final successful query generation result"
    )
    
    # Workflow status
    status: Literal["pending", "generating", "validating", "error_analysis", "completed", "failed"] = Field(
        default="pending", 
        description="Current workflow status"
    )
    
    # Context and metadata
    context_data: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional context data for the generation process"
    )
    
    # Performance tracking
    total_processing_time: float = Field(default=0.0, description="Total processing time in seconds")
    generation_start_time: Optional[float] = Field(default=None, description="Start time of generation process")
    
    @property
    def can_retry(self) -> bool:
        """Check if another generation attempt is allowed"""
        return self.current_attempt < self.max_attempts and self.status != "completed"
    
    @property 
    def has_successful_result(self) -> bool:
        """Check if we have a successful result"""
        return self.final_result is not None and self.final_result.success
    
    @property
    def latest_attempt(self) -> Optional[QueryGenerationResponse]:
        """Get the most recent generation attempt"""
        return self.generation_attempts[-1] if self.generation_attempts else None
    
    def add_generation_attempt(self, response: QueryGenerationResponse):
        """Add a new generation attempt to history"""
        self.generation_attempts.append(response)
        self.current_attempt += 1
        
        if response.success and self.validation_passed:
            self.final_result = response
            self.status = "completed"
    
    def add_error_analysis(self, analysis: QueryErrorAnalysis):
        """Add error analysis to history"""
        self.error_history.append(analysis)
        self.last_error = analysis.error_message
    
    def update_status(self, new_status: Literal["pending", "generating", "validating", "error_analysis", "completed", "failed"]):
        """Update the current workflow status"""
        self.status = new_status
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """Get a summary of the generation process for debugging"""
        return {
            "status": self.status,
            "attempts": f"{self.current_attempt}/{self.max_attempts}",
            "validation_passed": self.validation_passed,
            "has_result": self.has_successful_result,
            "generation_strategy": self.generation_strategy,
            "error_count": len(self.error_history),
            "processing_time": self.total_processing_time,
            "latest_confidence": self.latest_attempt.confidence if self.latest_attempt else 0.0
        }


class QueryGenerationContext(TSModel):
    """Context information for query generation"""
    
    # Database context
    database_type: str = Field(description="Target database type")
    schema_complexity: Literal["simple", "moderate", "complex"] = Field(
        default="moderate", 
        description="Assessed complexity of database schema"
    )
    
    # Query context
    query_complexity: Literal["simple", "moderate", "complex"] = Field(
        default="moderate", 
        description="Assessed complexity of required query"
    )
    query_type: Literal["select", "aggregation", "join", "analytical", "exploration"] = Field(
        default="select", 
        description="Type of query being generated"
    )
    
    # Performance context
    expected_result_size: Literal["small", "medium", "large"] = Field(
        default="medium", 
        description="Expected size of query results"
    )
    performance_requirements: List[str] = Field(
        default_factory=list, 
        description="Specific performance requirements"
    )
    
    # Domain context
    domain_hints: List[str] = Field(
        default_factory=list, 
        description="Domain-specific hints for query generation"
    )
    business_rules: List[str] = Field(
        default_factory=list, 
        description="Business rules to consider"
    )
    
    # Exploration context
    exploration_findings: Optional[str] = Field(
        default=None, 
        description="Previous data exploration findings"
    )
    data_quality_notes: List[str] = Field(
        default_factory=list, 
        description="Data quality considerations"
    )


class QueryValidationState(TSModel):
    """State for query validation process"""
    
    query_to_validate: str = Field(description="Query being validated")
    database_type: str = Field(description="Target database type")
    
    # Validation steps
    syntax_check_passed: bool = Field(default=False, description="Whether syntax validation passed")
    semantic_check_passed: bool = Field(default=False, description="Whether semantic validation passed")
    performance_check_passed: bool = Field(default=False, description="Whether performance check passed")
    
    # Validation results
    validation_results: List[QueryValidationResult] = Field(
        default_factory=list, 
        description="History of validation attempts"
    )
    
    # Issues found
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues that must be fixed")
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")
    suggestions: List[str] = Field(default_factory=list, description="Optimization suggestions")
    
    @property
    def is_valid(self) -> bool:
        """Check if query passed all validation checks"""
        return (self.syntax_check_passed and 
                self.semantic_check_passed and 
                len(self.critical_issues) == 0)
    
    @property
    def validation_score(self) -> float:
        """Calculate overall validation score (0-1)"""
        score = 0.0
        if self.syntax_check_passed:
            score += 0.4
        if self.semantic_check_passed:
            score += 0.4
        if self.performance_check_passed:
            score += 0.2
        
        # Penalize for critical issues
        if self.critical_issues:
            score -= min(0.3, len(self.critical_issues) * 0.1)
        
        return max(0.0, score) 