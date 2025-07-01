from typing import Dict, Any, List, Optional
from pydantic import Field
from doorbeen.core.types.ts_model import TSModel


class AgentHandoff(TSModel):
    """Represents a handoff between agents with context"""
    source_agent: str
    target_agent: str
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None
    
    
class DataAnalysisContext(TSModel):
    """Context for Data Analysis Agent operations"""
    schema_analyzed: bool = False
    tables_explored: List[str] = Field(default_factory=list)
    domain_detected: Optional[str] = None
    relevant_tables: List[str] = Field(default_factory=list)
    table_relationships: Dict[str, List[str]] = Field(default_factory=dict)
    data_quality_issues: List[str] = Field(default_factory=list)
    exploration_queries_executed: List[str] = Field(default_factory=list)
    schema_confidence: float = 0.0  # 0.0 to 1.0
    analysis_notes: List[str] = Field(default_factory=list)


class QueryGenerationContext(TSModel):
    """Context for Query Generation Agent operations"""
    query_generated: bool = False  # Track if query has been generated
    query_validated: bool = False  # Track if query has been validated
    needs_optimization: bool = False  # Track if query needs optimization
    generation_confidence: Optional[float] = None  # Confidence score for generated query
    sql_queries_generated: List[str] = Field(default_factory=list)
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    optimization_applied: List[str] = Field(default_factory=list)
    syntax_errors_fixed: List[str] = Field(default_factory=list)
    performance_warnings: List[str] = Field(default_factory=list)
    query_complexity: Optional[str] = None  # simple, moderate, complex
    generation_strategy: Optional[str] = None  # direct, iterative, fallback
    alternative_queries: List[str] = Field(default_factory=list)


class ResultProcessingContext(TSModel):
    """Context for Result Processing Agent operations"""
    results_analyzed: bool = False
    insights_extracted: List[str] = Field(default_factory=list)
    statistical_summaries: Dict[str, Any] = Field(default_factory=dict)
    visualizations_suggested: List[str] = Field(default_factory=list)
    anomalies_detected: List[str] = Field(default_factory=list)
    data_patterns: List[str] = Field(default_factory=list)
    confidence_level: float = 0.0  # 0.0 to 1.0
    processing_notes: List[str] = Field(default_factory=list)


class ObjectiveEvaluationContext(TSModel):
    """Context for Objective Evaluation Agent operations"""
    objectives_identified: List[str] = Field(default_factory=list)
    completion_assessments: List[Dict[str, Any]] = Field(default_factory=list)
    missing_objectives: List[str] = Field(default_factory=list)
    completion_confidence: float = 0.0  # 0.0 to 1.0
    evaluation_reasoning: List[str] = Field(default_factory=list)
    next_steps_suggested: List[str] = Field(default_factory=list)
    overall_completion_status: Optional[str] = None  # complete, partial, insufficient


class FinalizationContext(TSModel):
    """Context for Finalization Agent operations"""
    answer_formatted: bool = False
    alternative_suggestions: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    formatting_style: Optional[str] = None  # detailed, summary, bullet_points
    user_guidance_provided: List[str] = Field(default_factory=list)
    limitations_noted: List[str] = Field(default_factory=list)
    finalization_notes: List[str] = Field(default_factory=list)


class AgentRetryConfiguration(TSModel):
    """Configuration for agent retry behavior"""
    max_retries: int
    current_retries: int = 0
    retry_strategies: List[str] = Field(default_factory=list)
    failed_attempts: List[Dict[str, Any]] = Field(default_factory=list)
    
    @property
    def can_retry(self) -> bool:
        return self.current_retries < self.max_retries
    
    def increment_retry(self, strategy: str, error: str):
        """Increment retry count and log the failed attempt"""
        self.current_retries += 1
        self.failed_attempts.append({
            "attempt": self.current_retries,
            "strategy": strategy,
            "error": error,
        })
        if strategy not in self.retry_strategies:
            self.retry_strategies.append(strategy)


class AgentCoordinationState(TSModel):
    """Overall coordination context for multi-agent system"""
    current_agent: Optional[str] = None
    agent_sequence: List[str] = Field(default_factory=list)
    handoff_history: List[AgentHandoff] = Field(default_factory=list)
    agents_completed: List[str] = Field(default_factory=list)
    agents_failed: List[str] = Field(default_factory=list)
    
    # Agent-specific contexts
    data_analysis: DataAnalysisContext = Field(default_factory=DataAnalysisContext)
    query_generation: QueryGenerationContext = Field(default_factory=QueryGenerationContext)
    result_processing: ResultProcessingContext = Field(default_factory=ResultProcessingContext)
    objective_evaluation: ObjectiveEvaluationContext = Field(default_factory=ObjectiveEvaluationContext)
    finalization: FinalizationContext = Field(default_factory=FinalizationContext)
    
    # Agent retry configurations
    agent_retries: Dict[str, AgentRetryConfiguration] = Field(default_factory=lambda: {
        "data_analysis": AgentRetryConfiguration(max_retries=2),
        "query_generation": AgentRetryConfiguration(max_retries=3),
        "result_processing": AgentRetryConfiguration(max_retries=2),
        "objective_evaluation": AgentRetryConfiguration(max_retries=1),
        "finalization": AgentRetryConfiguration(max_retries=1),
    })
    
    # Supervisor decision tracking
    supervisor_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    coordination_notes: List[str] = Field(default_factory=list)
    
    def add_handoff(self, handoff: AgentHandoff):
        """Add a handoff to the history"""
        self.handoff_history.append(handoff)
        self.current_agent = handoff.target_agent
        if handoff.target_agent not in self.agent_sequence:
            self.agent_sequence.append(handoff.target_agent)
    
    def mark_agent_completed(self, agent_name: str, result: Dict[str, Any] = None):
        """Mark an agent as successfully completed with optional result"""
        if agent_name not in self.agents_completed:
            self.agents_completed.append(agent_name)
        if agent_name in self.agents_failed:
            self.agents_failed.remove(agent_name)
        
        # Log the completion
        self.coordination_notes.append(f"Agent {agent_name} completed successfully")
        if result:
            self.coordination_notes.append(f"Result: {str(result)[:100]}...")  # Truncate long results
    
    def mark_agent_failed(self, agent_name: str, error: str = None):
        """Mark an agent as failed with optional error message"""
        if agent_name not in self.agents_failed:
            self.agents_failed.append(agent_name)
        
        # Log the failure
        error_msg = f"Agent {agent_name} failed"
        if error:
            error_msg += f": {error}"
        self.coordination_notes.append(error_msg)
    
    def set_current_agent(self, agent_name: str):
        """Set the current active agent"""
        self.current_agent = agent_name
        if agent_name not in self.agent_sequence:
            self.agent_sequence.append(agent_name)
    
    def get_current_agent(self) -> Optional[str]:
        """Get the current active agent"""
        return self.current_agent
    
    def get_completed_agents(self) -> List[str]:
        """Get list of completed agents"""
        return self.agents_completed.copy()
    
    def get_failed_agents(self) -> List[str]:
        """Get list of failed agents"""
        return self.agents_failed.copy()
    
    def get_agent_retry_config(self, agent_name: str) -> AgentRetryConfiguration:
        """Get retry configuration for a specific agent"""
        return self.agent_retries.get(agent_name, AgentRetryConfiguration(max_retries=1))
    
    def get_agent_status(self, agent_name: str) -> str:
        """Get the current status of an agent"""
        if agent_name in self.agents_completed:
            return "completed"
        elif agent_name in self.agents_failed:
            return "failed"
        elif agent_name == self.current_agent:
            return "active"
        elif agent_name in self.agent_sequence:
            return "processed"
        else:
            return "pending"
    
    def add_supervisor_decision(self, decision: str, reasoning: str, context: Dict[str, Any] = None):
        """Log a supervisor decision"""
        self.supervisor_decisions.append({
            "decision": decision,
            "reasoning": reasoning,
            "context": context or {},
            "agent_sequence_at_decision": self.agent_sequence.copy(),
        }) 