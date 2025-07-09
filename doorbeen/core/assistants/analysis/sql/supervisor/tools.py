"""
Supervisor-compatible tools for SQL analysis agents.

These tools are designed to work with SQLSupervisorState and can be injected
into agents using InjectedState pattern.
"""

import json
from typing import Annotated, Dict, Any, List
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedState
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.models.provider import ModelHandler
from pydantic import ConfigDict


class QuestionClassification(TSModel):
    """Structured response for question classification."""
    classification_type: str = Field(description="Type of question: 'general_knowledge' or 'data_analysis_required'")
    routing_decision: str = Field(description="Routing decision: 'answer_directly' or 'use_data_agents'")
    confidence_level: str = Field(description="Confidence level: 'high', 'medium', or 'low'")
    reasoning: str = Field(description="Brief explanation of the classification decision")
    requires_database: bool = Field(description="Whether the question requires database access")
    model_config = ConfigDict(extra="forbid")


@tool
async def classify_question_type(
    user_question: str,
    state: Annotated[dict, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"]
) -> str:
    """
    Classify whether a question requires data analysis or can be answered directly using LLM.
    
    Uses the model to intelligently classify questions with high accuracy.
    """
    
    # Get handler from config
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not available"})
    
    classification_prompt = f"""
You are an expert question classifier. Analyze the following question and classify it as either:

1. **GENERAL KNOWLEDGE** - Questions that can be answered using your training data without accessing any database:
   - Facts about people, places, history, science, etc.
   - Definitions and explanations
   - General world knowledge
   - Examples: "Who is the prime minister of India?", "What is the capital of France?", "When was Google founded?"

2. **DATA ANALYSIS REQUIRED** - Questions that require accessing a database or personal data:
   - Questions about personal data, activities, health metrics
   - Questions asking for specific data from databases
   - Questions requiring counts, calculations, or analysis of stored data
   - Examples: "How many steps did I take?", "What time do I sleep?", "Show my data"

Question to classify: "{user_question}"

Respond with a JSON object containing:
- classification_type: "general_knowledge" or "data_analysis_required"
- routing_decision: "answer_directly" or "use_data_agents"
- confidence_level: "high", "medium", or "low"
- reasoning: Brief explanation of your decision
- requires_database: true/false
Be conservative - when in doubt, classify as "data_analysis_required" to avoid missing important queries.
"""
    
    try:
        # Use structured output for reliable JSON parsing
        json_llm = handler.model.bind(response_format={"type": "json_object"})
        response = await json_llm.ainvoke(classification_prompt)
        
        # Parse the JSON response
        classification_data = json.loads(response.content)
        
        # Store classification in state
        state["question_classification"] = classification_data
        
        return json.dumps({
            "success": True,
            "classification": classification_data["classification_type"],
            "routing": classification_data["routing_decision"],
            "confidence": classification_data["confidence_level"],
            "reasoning": classification_data["reasoning"]
        })
        
    except Exception as e:
        # Fallback to data analysis if classification fails
        fallback_classification = {
            "classification_type": "data_analysis_required",
            "routing_decision": "use_data_agents",
            "confidence_level": "low",
            "reasoning": f"Classification failed, defaulting to data analysis: {str(e)}",
            "requires_database": True
        }
        
        state["question_classification"] = fallback_classification
        
        return json.dumps({
            "success": False,
            "error": str(e),
            "fallback_classification": fallback_classification
        })


@tool
async def answer_general_knowledge_question(
    user_question: str,
    state: Annotated[dict, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"]
) -> str:
    """
    Answer general knowledge questions directly using the model's knowledge base.
    
    This tool should only be used for questions classified as general knowledge.
    """
    
    # Get handler from config
    configuration = config.get("configurable", {})
    handler: ModelHandler = configuration.get("handler")
    
    if not handler:
        return json.dumps({"success": False, "error": "Model handler not available"})
    
    # Create a prompt to answer the general knowledge question
    answer_prompt = f"""
You are answering a general knowledge question. Provide a clear, accurate, and concise answer based on your training data.

Question: {user_question}

Provide a direct, factual answer. Be confident and authoritative since this has been classified as general knowledge that you should know.
"""
    
    try:
        response = await handler.model.ainvoke(answer_prompt)
        
        # Store the answer in state
        state["final_answer"] = response.content
        state["is_complete"] = True
        state["workflow_completed"] = True
        state["skip_finalization"] = True  # Skip finalizer for simple answers
        
        return json.dumps({
            "success": True,
            "answer": response.content,
            "message": "General knowledge question answered directly"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to answer general knowledge question: {str(e)}"
        })


@tool
def get_objective_from_state(
    state: Annotated[dict, InjectedState]
) -> str:
    """Get the current objective/user question from the state."""
    # Try multiple possible keys for the user question
    user_question = state.get("input") or state.get("user_question") or state.get("objective")
    
    if not user_question:
        # If no question found, try to extract from messages
        messages = state.get("messages", [])
        for message in messages:
            if hasattr(message, 'content') and message.content:
                return f"Objective extracted from messages: {message.content}"
        return "No objective specified"
    
    return user_question


@tool
def get_schema_context(
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """Get the current schema context from the state."""
    schema_context = state.get("schema_context")
    
    if not schema_context:
        return {
            "available": False,
            "message": "No schema context available - schema exploration needed",
            "tables": [],
            "context": {}
        }
    
    return {
        "available": True,
        "message": "Schema context is available",
        "tables": schema_context.get("tables", []),
        "context": schema_context
    }


@tool
def update_schema_context(
    schema_info: Dict[str, Any],
    state: Annotated[dict, InjectedState]
) -> str:
    """Update schema context in state."""
    if state["schema_context"] is None:
        state["schema_context"] = {}
    state["schema_context"].update(schema_info)
    return "Schema context updated successfully"


@tool
def get_sql_query(
    state: Annotated[dict, InjectedState]
) -> str:
    """Get the current SQL query from state."""
    return state["sql_query"] or "No SQL query generated yet"


@tool
def update_sql_query(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Update the SQL query in state."""
    state["sql_query"] = query
    return "SQL query updated successfully"


@tool
def get_execution_results(
    state: Annotated[dict, InjectedState]
) -> List[Dict[str, Any]]:
    """Get query execution results from state."""
    return state["execution_results"] or []


@tool
def update_execution_results(
    results: List[Dict[str, Any]],
    state: Annotated[dict, InjectedState]
) -> str:
    """Update execution results in state."""
    state["execution_results"] = results
    return "Execution results updated successfully"


@tool
def get_analysis_summary(
    state: Annotated[dict, InjectedState]
) -> str:
    """Get analysis summary from state."""
    return state["analysis_summary"] or "No analysis completed yet"


@tool
def update_analysis_summary(
    summary: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Update analysis summary in state."""
    state["analysis_summary"] = summary
    return "Analysis summary updated successfully"


@tool
def evaluate_objectives_completion(
    state: Annotated[dict, InjectedState]
) -> str:
    """
    Evaluate whether the user's objectives have been met.
    
    Returns status indicating completion level.
    """
    objective = state["input"]
    has_query = bool(state["sql_query"])
    has_results = bool(state["execution_results"])
    has_analysis = bool(state["analysis_summary"])
    
    # Check if this is a general knowledge question that was answered directly
    question_classification = state.get("question_classification", {})
    if question_classification.get("routing_decision") == "answer_directly":
        state["objectives_met"] = "all_objectives_met"
        return "General knowledge question - objectives completed without data analysis"
    
    if not objective:
        return "No clear objective to evaluate"
    
    if not has_query:
        state.objectives_met = "needs_query_generation"
        return "Needs SQL query generation to proceed"
    
    if not has_results:
        state.objectives_met = "needs_execution"
        return "SQL query exists but needs execution"
    
    if not has_analysis:
        state.objectives_met = "needs_analysis" 
        return "Results exist but need analysis to answer user's question"
    
    # Check if we have a comprehensive answer
    if state["final_answer"]:
        state["objectives_met"] = "all_objectives_met"
        return "All objectives completed - user question fully answered"
    
    state["objectives_met"] = "needs_finalization"
    return "Analysis complete but needs final answer formatting"


@tool
def update_final_answer(
    answer: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Update the final answer in state."""
    state["final_answer"] = answer
    return "Final answer updated and marked complete"


@tool
def set_error(
    error_message: str,
    state: Annotated[dict, InjectedState],
    error_type: str = "general"
) -> str:
    """Set error information in state."""
    state["error"] = {
        "type": error_type,
        "message": error_message
    }
    return f"Error logged: {error_message}"


@tool
def get_current_status(
    state: Annotated[dict, InjectedState]
) -> Dict[str, Any]:
    """Get current status summary of the analysis with detailed progress information."""
    
    user_question = state.get("input", "")
    schema_context = state.get("schema_context")
    sql_query = state.get("sql_query") 
    execution_results = state.get("execution_results")
    data_summary = state.get("data_summary")
    final_answer = state.get("final_answer")
    error = state.get("error")
    question_classification = state.get("question_classification", {})
    
    status = {
        "user_question": user_question,
        "has_user_question": bool(user_question and user_question != "No objective specified"),
        "question_classification": question_classification,
        "has_schema_context": bool(schema_context),
        "has_sql_query": bool(sql_query),
        "has_execution_results": bool(execution_results),
        "has_data_summary": bool(data_summary),
        "has_final_answer": bool(final_answer),
        "has_error": bool(error),
        "is_complete": state.get("is_complete", False),
        "skip_finalization": state.get("skip_finalization", False),
        
        # Enhanced routing guidance
        "routing_recommendation": _determine_next_step(state),
        
        # Detailed status for each phase
        "phase_status": {
            "question_classified": bool(question_classification),
            "schema_explored": bool(schema_context),
            "query_generated": bool(sql_query),
            "data_retrieved": bool(execution_results),
            "analysis_complete": bool(data_summary),
            "answer_finalized": bool(final_answer)
        }
    }
    
    return status


def _determine_next_step(state: Dict[str, Any]) -> str:
    """Determine the recommended next step based on current state."""
    
    question_classification = state.get("question_classification", {})
    
    # If it's a general knowledge question, answer directly
    if question_classification.get("routing_decision") == "answer_directly":
        if not state.get("final_answer"):
            return "answer_general_knowledge_question"
        else:
            return "complete"
    
    # For data analysis questions, follow the complete workflow
    if not state.get("schema_context"):
        return "transfer_to_DataAnalyst"
    elif not state.get("sql_query") or not state.get("execution_results"):
        return "transfer_to_QueryGenerator"
    elif not state.get("final_insights") and not state.get("insights_summary"):
        return "transfer_to_ResultProcessor"
    elif not state.get("final_answer"):
        return "transfer_to_Finalizer"
    else:
        return "complete"


@tool
def check_query_execution_status(state: Annotated[dict, InjectedState]) -> str:
    """
    Check the current status of query execution by examining state data.
    
    Returns:
        str: Status description for routing decisions
    """
    try:
        # Get execution results from state (populated by tools)
        execution_results = state.get("execution_results", [])
        sql_query = state.get("sql_query", "")
        query_validation_status = state.get("query_validation_status", {})
        
        # Check if we have a successfully executed query with results
        if sql_query and execution_results:
            result_count = len(execution_results) if isinstance(execution_results, list) else 0
            
            # Check if results have been processed by ResultProcessor
            final_insights = state.get("final_insights", "")
            insights_summary = state.get("insights_summary", {})
            
            if final_insights or insights_summary:
                return f"""
✅ COMPREHENSIVE ANALYSIS COMPLETED

📊 **Analysis Results Summary:**
- **SQL Query:** {sql_query[:100]}{'...' if len(sql_query) > 100 else ''}
- **Results:** {result_count} rows analyzed
- **Insights Generated:** ✅ Complete
- **Analysis Components:** {len(insights_summary.get('analysis_components_used', []))} components used

🎯 **Next Step:** Route to Finalizer to format and present final answer.

**State Data Available:**
- sql_query: ✅ Present
- execution_results: ✅ Present ({result_count} rows)
- final_insights: ✅ Present
- insights_summary: ✅ Present
"""
            else:
                return f"""
📊 QUERY EXECUTION COMPLETED - ANALYSIS NEEDED

📊 **Query Results Summary:**
- **SQL Query:** {sql_query[:100]}{'...' if len(sql_query) > 100 else ''}
- **Results:** {result_count} rows returned
- **Validation Status:** {query_validation_status.get('status', 'unknown')}
- **Analysis Status:** Not yet processed

🎯 **Next Step:** Route to ResultProcessor for comprehensive data analysis.

**State Data Available:**
- sql_query: ✅ Present
- execution_results: ✅ Present ({result_count} rows)
- final_insights: ❌ Missing (needs ResultProcessor)
"""
        
        # Check if query exists but no results yet
        elif sql_query and not execution_results:
            validation_status = query_validation_status.get('status', 'unknown')
            
            if validation_status == 'failed':
                return f"""
❌ QUERY VALIDATION FAILED

🔍 **Issue:** Query generated but validation failed
- **SQL Query:** {sql_query[:100]}{'...' if len(sql_query) > 100 else ''}
- **Validation Error:** {query_validation_status.get('error', 'Unknown validation error')}

🎯 **Next Step:** Route back to QueryGenerator to fix validation issues.
"""
            else:
                return f"""
⏳ QUERY GENERATED BUT NOT EXECUTED

🔍 **Status:** Query exists but execution not completed
- **SQL Query:** {sql_query[:100]}{'...' if len(sql_query) > 100 else ''}
- **Validation Status:** {validation_status}

🎯 **Next Step:** Continue with QueryGenerator to complete execution.
"""
        
        # Check if we have comprehensive context but no query yet
        schema_context = state.get("schema_context", {})
        table_examples = state.get("table_examples", {})
        
        if schema_context and table_examples:
            return f"""
📋 CONTEXT AVAILABLE - READY FOR QUERY GENERATION

🔍 **Available Context:**
- **Schema:** {schema_context.get('total_tables', 0)} tables analyzed
- **Sample Data:** {len(table_examples)} tables sampled
- **Database Type:** {schema_context.get('database_type', 'unknown')}

🎯 **Next Step:** Route to QueryGenerator to create and execute query.
"""
        
        # Check if we have basic schema but need more context
        elif schema_context:
            return f"""
📊 SCHEMA RETRIEVED - NEED COMPREHENSIVE CONTEXT

🔍 **Current Status:**
- **Schema:** {schema_context.get('total_tables', 0)} tables available
- **Sample Data:** Missing
- **Context:** Incomplete

🎯 **Next Step:** Continue with DataAnalyst to complete context gathering.
"""
        
        # No significant progress yet
        else:
            return f"""
🚀 ANALYSIS STARTING

🔍 **Current Status:**
- **Schema:** Not retrieved
- **Context:** Not available
- **Query:** Not generated

🎯 **Next Step:** Route to DataAnalyst to begin schema analysis.
"""
            
    except Exception as e:
        # logger.error(f"[CHECK_QUERY_STATUS] Error checking status: {e}") # Original code had this line commented out
        return f"""
❌ STATUS CHECK ERROR

🔍 **Error:** {str(e)}

🎯 **Next Step:** Route to DataAnalyst to restart analysis process.
"""


@tool
def add_handoff_context(
    context_key: str,
    context_value: Any,
    state: Annotated[dict, InjectedState]
) -> str:
    """Add context information for agent handoffs."""
    if state.get("handoff_context") is None:
        state["handoff_context"] = {}
    state["handoff_context"][context_key] = context_value
    return f"Added handoff context: {context_key}"


@tool
def get_handoff_context(
    context_key: str,
    state: Annotated[dict, InjectedState]
) -> Any:
    """Get handoff context information."""
    handoff_context = state.get("handoff_context", {})
    return handoff_context.get(context_key, f"No context found for key: {context_key}")


# Tools grouped by agent type for easy assignment
DATA_ANALYSIS_TOOLS = [
    get_objective_from_state,
    get_schema_context,
    update_schema_context,
    add_handoff_context,
    get_current_status
]

QUERY_GENERATION_TOOLS = [
    get_objective_from_state,
    get_schema_context,
    get_sql_query,
    update_sql_query,
    update_execution_results,
    set_error,
    add_handoff_context,
    get_current_status
]

RESULT_PROCESSING_TOOLS = [
    get_objective_from_state,
    get_execution_results,
    get_analysis_summary,
    update_analysis_summary,
    add_handoff_context,
    get_current_status
]

OBJECTIVE_EVALUATION_TOOLS = [
    get_objective_from_state,
    evaluate_objectives_completion,
    get_current_status,
    add_handoff_context
]

FINALIZATION_TOOLS = [
    get_objective_from_state,
    get_analysis_summary,
    get_execution_results,
    update_final_answer,
    get_current_status
] 