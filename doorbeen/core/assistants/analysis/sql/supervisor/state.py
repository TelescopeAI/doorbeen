from typing import List, Optional, Dict, Any

from langgraph.prebuilt.chat_agent_executor import AgentStateWithStructuredResponse


class SQLSupervisorState(AgentStateWithStructuredResponse):
    """
    State schema for the SQL Analysis Supervisor.
    
    This state is designed to be comprehensive, tracking the outputs from each specialist agent
    to provide a full picture of the analysis process for the supervisor and subsequent agents.
    """

    # A list to hold agent lifecycle events for UI streaming,
    # without interfering with the LLM conversation history.
    agent_lifecycle_events: Optional[List[Dict[str, Any]]] = None

    # Core user request
    input: str

    # Overall analysis status
    is_complete: bool = False
    error: Optional[Dict[str, Any]] = None

    # Agent routing and management
    current_agent: Optional[str] = None
    agent_sequence: List[str] = []
    handoff_context: Optional[Dict[str, Any]] = None

    # --- Agent-specific outputs ---

    # 1. DataAnalysisAgent output
    schema_summary: Optional[str] = None
    relevant_tables: Optional[List[str]] = None

    # 2. QueryGenerationAgent output
    sql_query: Optional[str] = None
    query_validation_error: Optional[str] = None
    execution_results: Optional[List[Dict[str, Any]]] = None

    # 3. ResultProcessingAgent output
    data_summary: Optional[str] = None
    trends_and_patterns: Optional[List[str]] = None
    key_insights: Optional[List[str]] = None

    # 4. ObjectiveEvaluationAgent output
    objective_evaluation: Optional[Dict[str, Any]] = None

    # 5. FinalizationAgent output
    final_summary: Optional[str] = None
    visualization_suggestions: Optional[List[str]] = None
    follow_up_questions: Optional[List[str]] = None
    final_answer: Optional[str] = None 