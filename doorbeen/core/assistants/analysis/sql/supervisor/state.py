from typing import List, Optional, Dict, Any, Sequence
from typing_extensions import Annotated

from langgraph.prebuilt.chat_agent_executor import AgentStateWithStructuredResponse


def add_events(left: Optional[List[Dict[str, Any]]], right: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Custom reducer function to append new events to the existing list of agent lifecycle events.
    Similar to how add_messages works for the messages field.
    """
    if left is None:
        left = []
    if right is None:
        right = []
    
    # Convert to lists if they aren't already
    if not isinstance(left, list):
        left = list(left) if left else []
    if not isinstance(right, list):
        right = list(right) if right else []
    
    # Return concatenated list
    return left + right


class SQLSupervisorState(AgentStateWithStructuredResponse):
    """
    State schema for the SQL Analysis Supervisor.
    
    This state is designed to be comprehensive, tracking the outputs from each specialist agent
    to provide a full picture of the analysis process for the supervisor and subsequent agents.
    Enhanced to support the draft-validate-execute workflow and intelligent question classification.
    """

    # A list to hold agent lifecycle events for UI streaming,
    # with a custom reducer to append events instead of overwriting them
    agent_lifecycle_events: Annotated[Sequence[Dict[str, Any]], add_events] = []

    # Core user request
    input: str

    # Overall analysis status
    is_complete: bool = False
    error: Optional[Dict[str, Any]] = None

    # Agent routing and management
    current_agent: Optional[str] = None
    agent_sequence: List[str] = []
    handoff_context: Optional[Dict[str, Any]] = None

    # Question classification for intelligent routing
    question_classification: Optional[Dict[str, Any]] = None
    skip_finalization: bool = False  # Skip finalizer for simple answers

    # --- Agent-specific outputs ---

    # 1. DataAnalysisAgent output - Enhanced with query planning
    schema_context: Optional[Dict[str, Any]] = None
    schema_summary: Optional[str] = None
    relevant_tables: Optional[List[str]] = None
    
    # New: Query planning from DataAnalyst to QueryGenerator
    query_plan: Optional[str] = None  # Text-based detailed plan for query generation (changed from Dict)
    table_examples: Optional[Dict[str, List[Dict[str, Any]]]] = None  # Sample data from relevant tables
    schema_analysis: Optional[Dict[str, Any]] = None  # Detailed schema analysis with data types
    query_strategy: Optional[str] = None  # High-level strategy for the query

    # 2. QueryGenerationAgent output - Enhanced for draft-validate-execute workflow
    sql_query: Optional[str] = None  # Final validated and executed query
    query_validation_error: Optional[str] = None
    execution_results: Optional[List[Dict[str, Any]]] = None
    
    # New fields for draft-validate-execute workflow
    draft_query: Optional[str] = None  # Current draft query being worked on
    validated_query: Optional[str] = None  # Query that passed validation
    previous_query_errors: Optional[List[Dict[str, Any]]] = None  # Error history for learning
    
    # Enhanced query generation tracking
    zero_result_attempts: int = 0  # Track attempts that returned 0 rows
    query_regeneration_reasons: Optional[List[str]] = None  # Reasons for query regeneration
    plan_updates: Optional[List[Dict[str, Any]]] = None  # Updates made to the original plan
    
    # Circuit breaker counters
    generation_attempts: int = 0
    validation_attempts: int = 0
    execution_attempts: int = 0
    
    # Enhanced context tracking
    comprehensive_context: Optional[Dict[str, Any]] = None
    sample_data_cache: Optional[Dict[str, Any]] = None  # Cached sample data from tables
    database_dialect: Optional[str] = None  # Detected database dialect
    
    # Query workflow status
    workflow_stage: Optional[str] = None  # Current stage: draft, validate, correct, execute
    workflow_completed: bool = False
    
    # 3. ResultProcessingAgent output
    data_summary: Optional[str] = None
    trends_and_patterns: Optional[List[str]] = None
    key_insights: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    
    # Enhanced result processing - detailed analysis results
    dataset_overview: Optional[Dict[str, Any]] = None
    top_values_analysis: Optional[Dict[str, Any]] = None
    aggregation_analysis: Optional[Dict[str, Any]] = None
    statistical_analysis: Optional[Dict[str, Any]] = None
    trend_analysis: Optional[Dict[str, Any]] = None
    correlation_analysis: Optional[Dict[str, Any]] = None
    outlier_analysis: Optional[Dict[str, Any]] = None
    categorical_analysis: Optional[Dict[str, Any]] = None
    analysis_strategy: Optional[str] = None  # "direct" or "aggregated"
    analysis_components_used: Optional[List[str]] = None
    
    # Grounding and examples
    past_examples: Optional[List[Dict[str, Any]]] = None
    similar_examples: Optional[List[Dict[str, Any]]] = None
    guidance_instructions: Optional[List[Dict[str, Any]]] = None
    expected_output_patterns: Optional[List[Dict[str, Any]]] = None
    guidance_applied: bool = False

    # 4. ObjectiveEvaluationAgent output
    objective_evaluation: Optional[Dict[str, Any]] = None

    # 5. FinalizationAgent output
    final_summary: Optional[str] = None
    visualization_suggestions: Optional[List[str]] = None
    follow_up_questions: Optional[List[str]] = None
    final_answer: Optional[str] = None 

    def mark_complete(self):
        """Mark the analysis as complete."""
        self.is_complete = True
        self.workflow_completed = True

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of the current analysis status."""
        return {
            "is_complete": self.is_complete,
            "question_classification": self.question_classification,
            "skip_finalization": self.skip_finalization,
            "has_schema": bool(self.schema_context),
            "has_query_plan": bool(self.query_plan),
            "has_table_examples": bool(self.table_examples),
            "has_query": bool(self.sql_query),
            "has_results": bool(self.execution_results),
            "has_analysis": bool(self.data_summary),
            "has_final_answer": bool(self.final_answer),
            "error": self.error,
            # Enhanced status for new workflow
            "workflow_stage": self.workflow_stage,
            "workflow_completed": self.workflow_completed,
            "has_draft_query": bool(self.draft_query),
            "has_validated_query": bool(self.validated_query),
            "zero_result_attempts": self.zero_result_attempts,
            "attempt_counts": {
                "generation": self.generation_attempts,
                "validation": self.validation_attempts,
                "execution": self.execution_attempts
            },
            "circuit_breaker_status": {
                "generation_limit_reached": self.generation_attempts >= 3,
                "validation_limit_reached": self.validation_attempts >= 5,
                "execution_limit_reached": self.execution_attempts >= 3
            }
        }

    def set_handoff_context(self, context: Dict[str, Any]):
        """Set context for agent handoffs."""
        if self.handoff_context is None:
            self.handoff_context = {}
        self.handoff_context.update(context)

    def get_handoff_context(self, key: str) -> Any:
        """Get handoff context value."""
        if self.handoff_context is None:
            return None
        return self.handoff_context.get(key)

    def reset_query_workflow(self):
        """Reset the query generation workflow for a fresh start."""
        self.draft_query = None
        self.validated_query = None
        self.generation_attempts = 0
        self.validation_attempts = 0
        self.execution_attempts = 0
        self.workflow_stage = None
        self.workflow_completed = False
        self.query_validation_error = None
        self.zero_result_attempts = 0

    def increment_generation_attempts(self) -> int:
        """Increment and return generation attempt counter."""
        self.generation_attempts += 1
        return self.generation_attempts

    def increment_validation_attempts(self) -> int:
        """Increment and return validation attempt counter."""
        self.validation_attempts += 1
        return self.validation_attempts

    def increment_execution_attempts(self) -> int:
        """Increment and return execution attempt counter."""
        self.execution_attempts += 1
        return self.execution_attempts

    def increment_zero_result_attempts(self) -> int:
        """Increment and return zero result attempt counter."""
        self.zero_result_attempts += 1
        return self.zero_result_attempts

    def add_query_error(self, query: str, error: str, error_type: str, attempt: int):
        """Add a query error to the error history for learning."""
        if self.previous_query_errors is None:
            self.previous_query_errors = []
        
        error_entry = {
            "query": query,
            "error": error,
            "error_type": error_type,
            "attempt": attempt,
            "timestamp": None  # Could add timestamp if needed
        }
        
        self.previous_query_errors.append(error_entry)
        
        # Keep only the last 10 errors to prevent state bloat
        if len(self.previous_query_errors) > 10:
            self.previous_query_errors = self.previous_query_errors[-10:]

    def add_query_regeneration_reason(self, reason: str):
        """Add a reason for query regeneration."""
        if self.query_regeneration_reasons is None:
            self.query_regeneration_reasons = []
        self.query_regeneration_reasons.append(reason)

    def add_plan_update(self, update_type: str, description: str, details: Dict[str, Any]):
        """Add an update to the query plan."""
        if self.plan_updates is None:
            self.plan_updates = []
        
        update_entry = {
            "type": update_type,
            "description": description,
            "details": details,
            "attempt": self.generation_attempts
        }
        
        self.plan_updates.append(update_entry)

    def get_error_patterns(self) -> List[str]:
        """Get common error patterns from error history."""
        if not self.previous_query_errors:
            return []
        
        error_types = [err.get("error_type", "unknown") for err in self.previous_query_errors]
        # Return unique error types
        return list(set(error_types))

    def is_circuit_breaker_triggered(self) -> bool:
        """Check if any circuit breaker has been triggered."""
        return (
            self.generation_attempts >= 3 or
            self.validation_attempts >= 5 or
            self.execution_attempts >= 3 or
            self.zero_result_attempts >= 3  # Circuit breaker for too many zero results
        )

    def should_regenerate_for_zero_results(self) -> bool:
        """Check if we should regenerate query due to zero results."""
        return self.zero_result_attempts < 2  # Allow up to 2 regenerations for zero results

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get detailed circuit breaker status."""
        return {
            "generation": {
                "current": self.generation_attempts,
                "limit": 3,
                "triggered": self.generation_attempts >= 3
            },
            "validation": {
                "current": self.validation_attempts,
                "limit": 5,
                "triggered": self.validation_attempts >= 5
            },
            "execution": {
                "current": self.execution_attempts,
                "limit": 3,
                "triggered": self.execution_attempts >= 3
            },
            "zero_results": {
                "current": self.zero_result_attempts,
                "limit": 3,
                "triggered": self.zero_result_attempts >= 3
            }
        }

    def update_workflow_stage(self, stage: str):
        """Update the current workflow stage."""
        valid_stages = ["draft", "validate", "correct", "execute", "complete"]
        if stage in valid_stages:
            self.workflow_stage = stage
            if stage == "complete":
                self.workflow_completed = True

    def is_general_knowledge_question(self) -> bool:
        """Check if this is a general knowledge question that can be answered directly."""
        classification = self.question_classification or {}
        return classification.get("routing") == "answer_directly"

    def should_skip_agents(self) -> bool:
        """Check if we should skip the agent workflow entirely."""
        return self.is_general_knowledge_question() and bool(self.final_answer)
