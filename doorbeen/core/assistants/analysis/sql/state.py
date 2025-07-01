from typing import List, Optional, Annotated, ClassVar, Dict, Any

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed.is_last_step import IsLastStepManager, RemainingStepsManager
from pydantic import Field

from doorbeen.core.assistants.analysis.grades import InputGradeResult
from doorbeen.core.assistants.analysis.sql.query.understanding import QueryUnderstanding
from doorbeen.core.types.enrich import EnrichedOutput
from doorbeen.core.types.execute import ExecutionResults
from doorbeen.core.types.generate import GeneratedSQLQuery
from doorbeen.core.types.observe import QueryAnalysisReport
from doorbeen.core.types.sql_schema import DatabaseSchema
from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.types.visualize import QueryVisualizationPlan
from doorbeen.core.assistants.analysis.sql.context.agent_contexts import AgentCoordinationState


def add_execution_operator(a: List[ExecutionResults], b: List[ExecutionResults]) -> List[ExecutionResults]:
    return a + b


class SQLAssistantState(TSModel):
    messages: Annotated[list[AnyMessage], add_messages]
    # Required fields for LangGraph supervisor compatibility
    is_last_step: Annotated[bool, IsLastStepManager] = False
    remaining_steps: Annotated[int, RemainingStepsManager] = 10
    error: Optional[dict] = None
    input: Optional[str] = Field(default=None, description="The current input question")
    should_enrich: Optional[bool] = Field(default=False, description="Whether the input needs to be enriched")
    enrich_output: Optional[EnrichedOutput] = Field(default=None, description="The output of the enrichment process")
    enrich_max_attempts: Optional[int] = Field(default=3, description="Maximum number of attempts to enrich the input")
    qa_passed: Optional[bool] = Field(default=False, description="Whether the input has passed QA")
    grade: Optional[InputGradeResult] = Field(default=None, description="The grade of the input")
    output: Optional[str] = Field(default=None, description="The output of the assistant")
    interpretation: Optional[QueryUnderstanding] = Field(default=None, description="Interpretation of the input")
    generated_query: Optional[GeneratedSQLQuery] = Field(default=None, description="The generated SQL query")
    execution_results: Optional[Annotated[list[ExecutionResults], add_execution_operator]] = Field(default=None,
                                                                                                   description="The result of executing the query")
    last_execution_failed: Optional[bool] = Field(default=False, description="Whether the last execution failed")
    query_observation_report: Optional[QueryAnalysisReport] = Field(default=None, description="Report on the query results")
    query_viz: Optional[QueryVisualizationPlan] = Field(default=None, description="Visualization of the query")
    selected_tables: Optional[List[str]] = Field(default_factory=list, description="Tables selected for the current "
                                                                                   "query")
    table_schemas: Optional[DatabaseSchema] = Field(default=None, description="Schemas of the selected tables")
    current_messages: Optional[List[AnyMessage]] = Field(default_factory=list,
                                                         description="Messages for the current execution")
    summary: Optional[str] = Field(default=None, description="Summary of the existing conversations")
    request_count: Optional[int] = Field(default=0, description="Number of requests made to the assistant")
    
    # Unified context management (replacing followup fields)
    conversation_context: Optional[str] = Field(default=None, description="Conversation context from previous messages")
    context_length: int = Field(default=0, description="Length of conversation context")
    
    # Circuit breaker fields
    retry_count: int = Field(default=0, description="Number of execution retries attempted")
    max_retries: int = Field(default=3, description="Maximum number of retries allowed")
    circuit_breaker_triggered: bool = Field(default=False, description="Whether circuit breaker has been triggered")
    last_execution_error: Optional[str] = Field(default=None, description="Last execution error message")
    execution_error_history: List[str] = Field(default_factory=list, description="History of execution errors")
    
    # Objective retry configuration
    objective_retry_count: int = Field(default=0, description="Number of retries specifically for unmet objectives")
    max_objective_retries: int = Field(default=2, description="Maximum retries when no objectives are met")
    objective_retry_strategies: List[str] = Field(default_factory=list, description="Track which retry strategies have been attempted")
    
    # Available retry strategies for unmet objectives
    AVAILABLE_RETRY_STRATEGIES: ClassVar[List[str]] = [
        "refine_interpretation",  # Re-interpret the question with more context
        "broader_search",         # Try a broader search approach
        "alternative_tables",     # Try different tables or data sources
        "simplified_query",       # Simplify the query to get basic results
        "related_analysis"        # Look for related data patterns
    ]
    
    # Data exploration fields
    data_exploration_complete: bool = Field(default=False, description="Whether data exploration phase is complete")
    exploration_findings: Optional[str] = Field(default=None, description="Findings from data exploration phase")
    schema_context: Optional[dict] = Field(default=None, description="Database schema context from analysis")
    domain_context: Optional[str] = Field(default=None, description="Domain context detected from database analysis")
    analysis_summary: Optional[dict] = Field(default=None, description="Summary of database analysis from data analysis agent")
    
    # Objective completion tracking
    objectives_met: Optional[str] = Field(default=None, description="Status of whether objectives are met: 'all_objectives_met', 'some_objectives_met', or None")
    has_actionable_results: bool = Field(default=False, description="Whether the query returned actionable results")
    alternative_suggestions_provided: bool = Field(default=False, description="Whether alternative suggestions were provided when no data found")
    
    # Enhanced enrichment fields (optional for backward compatibility)
    enriched_question: Optional[str] = Field(default=None, description="The enriched version of the input question")
    relevance_assessment: Optional[str] = Field(default=None, description="Assessment of question relevance to dataset")
    assumptions_made: Optional[List[str]] = Field(default_factory=list, description="List of assumptions made during enrichment")
    alternative_questions: Optional[List[str]] = Field(default_factory=list, description="Alternative question suggestions from enrichment")
    enrichment_strategy: Optional[str] = Field(default=None, description="Strategy used for enrichment (pattern-based, data-driven, etc.)")
    data_driven_thresholds: Optional[dict] = Field(default_factory=dict, description="Data-driven thresholds and constraints applied")
    
    # Multi-agent coordination context
    agent_coordination: AgentCoordinationState = Field(default_factory=AgentCoordinationState, description="Multi-agent coordination context")
    using_multi_agent: bool = Field(default=False, description="Whether using multi-agent supervisor architecture")
    supervisor_active: bool = Field(default=False, description="Whether supervisor is currently coordinating agents")
    
    # Query generation fields
    sql_query: Optional[str] = Field(default=None, description="Generated SQL query")
    query_explanation: Optional[str] = Field(default=None, description="Explanation of the generated query")
    query_confidence: Optional[float] = Field(default=None, description="Confidence score for the generated query")
    query_complexity: Optional[str] = Field(default=None, description="Complexity level of the generated query")
    query_validation_passed: bool = Field(default=False, description="Whether query validation passed")
    query_validation_errors: List[str] = Field(default_factory=list, description="Query validation error messages")
    
    # Query execution fields
    execution_results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Results from query execution")
    execution_error: Optional[str] = Field(default=None, description="Error message if query execution failed")
    execution_time: Optional[float] = Field(default=None, description="Query execution time in seconds")
    
    # Analysis results
    result_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Analysis of query results")
    objective_evaluation: Optional[Dict[str, Any]] = Field(default=None, description="Evaluation of whether objectives were met")
    final_answer: Optional[str] = Field(default=None, description="Final formatted answer to the user's question")
    
    @property
    def can_retry(self) -> bool:
        """Check if another retry attempt is allowed"""
        return self.retry_count < self.max_retries and not self.circuit_breaker_triggered
    
    @property
    def can_retry_objectives(self) -> bool:
        """Check if another objective retry attempt is allowed"""
        return (self.objective_retry_count < self.max_objective_retries and 
                not self.circuit_breaker_triggered and
                len(self.objective_retry_strategies) < len(self.AVAILABLE_RETRY_STRATEGIES))
    
    def get_next_retry_strategy(self) -> Optional[str]:
        """Get the next available retry strategy that hasn't been tried"""
        for strategy in self.AVAILABLE_RETRY_STRATEGIES:
            if strategy not in self.objective_retry_strategies:
                return strategy
        return None
    
    def mark_retry_strategy_used(self, strategy: str):
        """Mark a retry strategy as used"""
        if strategy not in self.objective_retry_strategies:
            self.objective_retry_strategies.append(strategy)
            self.objective_retry_count += 1
    
    @classmethod
    def create_with_retry_config(cls, max_retries: int = 3, max_objective_retries: int = 2, **kwargs):
        """Create a SQLAssistantState with custom retry configuration"""
        return cls(
            max_retries=max_retries,
            max_objective_retries=max_objective_retries,
            **kwargs
        )
    
    def get_retry_status_summary(self) -> dict:
        """Get a summary of current retry status for debugging/monitoring"""
        return {
            "execution_retries": f"{self.retry_count}/{self.max_retries}",
            "objective_retries": f"{self.objective_retry_count}/{self.max_objective_retries}",
            "strategies_tried": self.objective_retry_strategies,
            "strategies_remaining": [s for s in self.AVAILABLE_RETRY_STRATEGIES if s not in self.objective_retry_strategies],
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "can_retry_execution": self.can_retry,
            "can_retry_objectives": self.can_retry_objectives
        }
    
    # Multi-agent helper methods
    def enable_multi_agent_mode(self):
        """Enable multi-agent supervisor architecture"""
        self.using_multi_agent = True
        self.supervisor_active = True
    
    def disable_multi_agent_mode(self):
        """Disable multi-agent architecture (fallback to linear nodes)"""
        self.using_multi_agent = False
        self.supervisor_active = False
    
    def get_current_agent(self) -> Optional[str]:
        """Get the currently active agent"""
        return self.agent_coordination.current_agent
    
    def get_agent_sequence(self) -> List[str]:
        """Get the sequence of agents that have been involved"""
        return self.agent_coordination.agent_sequence.copy()
    
    def get_completed_agents(self) -> List[str]:
        """Get the list of agents that have completed successfully"""
        return self.agent_coordination.agents_completed.copy()
    
    def get_failed_agents(self) -> List[str]:
        """Get the list of agents that have failed"""
        return self.agent_coordination.agents_failed.copy()
    
    def can_agent_retry(self, agent_name: str) -> bool:
        """Check if an agent can retry"""
        retry_config = self.agent_coordination.get_agent_retry_config(agent_name)
        return retry_config.can_retry
    
    def get_multi_agent_status(self) -> dict:
        """Get comprehensive multi-agent status for monitoring"""
        return {
            "using_multi_agent": self.using_multi_agent,
            "supervisor_active": self.supervisor_active,
            "current_agent": self.get_current_agent(),
            "agent_sequence": self.get_agent_sequence(),
            "completed_agents": self.get_completed_agents(),
            "failed_agents": self.get_failed_agents(),
            "handoff_count": len(self.agent_coordination.handoff_history),
            "supervisor_decisions": len(self.agent_coordination.supervisor_decisions),
        }
    
    # Dictionary compatibility methods for LangGraph supervisor
    def __getitem__(self, key):
        """Make state dict-compatible for LangGraph"""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{key}' not found in state")
    
    def __setitem__(self, key, value):
        """Make state dict-compatible for LangGraph"""
        if key in self.__fields__:
            setattr(self, key, value)
        else:
            # For dynamic fields, use object.__setattr__ to bypass Pydantic validation
            object.__setattr__(self, key, value)
    
    def get(self, key, default=None):
        """Dict-like get method for LangGraph compatibility"""
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    
    def keys(self):
        """Return all field names for dict-like behavior"""
        # Return both Pydantic fields and any dynamic attributes
        pydantic_keys = set(self.__fields__.keys())
        dynamic_keys = set(key for key in self.__dict__.keys() if not key.startswith('_'))
        return pydantic_keys.union(dynamic_keys)
    
    def items(self):
        """Return key-value pairs for dict-like behavior"""
        for key in self.keys():
            yield key, getattr(self, key)
    
    def values(self):
        """Return all values for dict-like behavior"""
        for key in self.keys():
            yield getattr(self, key)
    
    def update(self, other):
        """Update state from another dict or state object"""
        if isinstance(other, dict):
            for key, value in other.items():
                self.__setitem__(key, value)
        elif hasattr(other, 'items'):
            for key, value in other.items():
                self.__setitem__(key, value)
    
    def copy(self):
        """Create a copy of the state"""
        return self.model_copy()
    
    # last_query: Optional[str] = Field(default=None, description="The last executed SQL query")
    # conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="History of the conversation")

    # def update_context(self, new_context: str):
    #     self.context += f"\n{new_context}"
    #
    # def add_query_result(self, result: Dict[str, Any]):
    #     self.query_results.append(result)
    #
    # def set_final_answer(self, answer: Dict[str, Any]):
    #     self.final_answer = answer
    #
    # def add_selected_table(self, table: str):
    #     if table not in self.selected_tables:
    #         self.selected_tables.append(table)
    #
    # def add_table_schema(self, table: str, schema: TableSchema):
    #     self.table_schemas[table] = schema
    #
    # def set_last_query(self, query: str):
    #     self.last_query = query
    #
    # def add_to_conversation(self, role: str, content: str):
    #     self.conversation_history.append({"role": role, "content": content})
    #
    # def clear_for_new_question(self):
    #     self.input = ""
    #     self.query_results = []
    #     self.final_answer = {}
    #     self.dag_info = {}
    #     self.last_query = None
    # Note: We're not clearing context, selected_tables, table_schemas, or conversation_history
    # as these might be useful for maintaining continuity across inputs
