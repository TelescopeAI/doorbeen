import json
from typing import List, Dict, Any
from typing_extensions import Annotated

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.assistants.analysis.sql.supervisor.state import SQLSupervisorState


@tool
async def create_final_summary(
    state: Annotated[dict, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Create a final, comprehensive summary using all available analysis context."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Creating comprehensive final summary with full analysis context...",
                "content": "📝 Generating complete analysis summary",
                "progress": 10
            }
        }
        
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
    
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "Finalization",
                "data": {
                    "scope": "Finalization",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for summary generation",
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
                    "error": {"type": "handler_error", "message": "Model handler not set"}
                }
            )

        # Extract comprehensive context from state
        user_question = state.get("input", "")
        query_plan = state.get("query_plan", {})
        sql_query = state.get("sql_query", "")
        execution_results = state.get("execution_results", [])
        data_summary = state.get("data_summary", "")
        trends_and_patterns = state.get("trends_and_patterns", [])
        key_insights = state.get("key_insights", [])
        query_strategy = state.get("query_strategy", "")
        database_dialect = state.get("database_dialect", "unknown")
        workflow_stage = state.get("workflow_stage", "")
        zero_result_attempts = state.get("zero_result_attempts", 0)
        schema_context = state.get("schema_context", {})
        table_examples = state.get("table_examples", {})
        
        # Emit processing progress
        processing_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": f"Processing complete analysis with {len(key_insights)} insights...",
                "content": f"⚙️ Synthesizing {query_strategy} analysis results",
                "progress": 30
            }
        }
        
        # Emit generation progress
        generation_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Generating comprehensive final summary...",
                "content": "🤖 AI creating complete analysis summary",
                "progress": 60
            }
        }
        
        # Create comprehensive final summary prompt
        prompt = f"""
You are a senior data analyst creating a comprehensive final summary of a complete data analysis workflow. Use all available context to provide a thorough, actionable summary.

USER QUESTION: {user_question}

ANALYSIS OVERVIEW:
- Query Strategy: {query_strategy}
- Database Type: {database_dialect}
- Workflow Stage: {workflow_stage}
- Zero Result Attempts: {zero_result_attempts}

QUERY PLAN CONTEXT:
{json.dumps(query_plan, indent=2) if query_plan else "No query plan available"}

EXECUTED SQL QUERY:
{sql_query}

DATA RESULTS ({len(execution_results)} rows):
{json.dumps(execution_results[:5], indent=2) if execution_results else "No results"}
{f"... and {len(execution_results) - 5} more rows" if len(execution_results) > 5 else ""}

DATA SUMMARY:
{data_summary}

IDENTIFIED TRENDS AND PATTERNS:
{chr(10).join(trends_and_patterns) if trends_and_patterns else "No trends identified"}

KEY INSIGHTS:
{chr(10).join(key_insights) if key_insights else "No key insights available"}

SCHEMA CONTEXT:
{json.dumps(schema_context, indent=2) if schema_context else "No schema context"}

TABLE EXAMPLES USED:
{json.dumps(table_examples, indent=2) if table_examples else "No table examples"}

FINAL SUMMARY REQUIREMENTS:
1. Provide a comprehensive summary that directly addresses the user's question
2. Include the key findings and their significance
3. Reference the data analysis methodology used
4. Explain how the SQL query addressed the user's needs
5. Highlight the most important insights and patterns
6. Include relevant statistics and data points
7. Explain any limitations or data quality considerations
8. If zero results, explain why and what it means
9. Make the summary accessible to both technical and non-technical audiences
10. Connect findings to actionable recommendations where appropriate

Create a detailed, well-structured final summary that provides complete closure to the user's analysis request.
"""
        
        response = await handler.model.ainvoke(prompt)
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Comprehensive final summary created",
                "content": "✅ Complete analysis summary generated",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Comprehensive final summary created",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, processing_progress_event, generation_progress_event, completion_progress_event],
                "final_summary": response.content
            }
        )
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": f"Summary generation failed: {str(e)}",
                "content": "❌ Failed to create final summary",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Summary generation failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "summary_error", "message": str(e)}
            }
        )


@tool
async def generate_visualizations(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Generate visualization suggestions based on comprehensive analysis context."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Analyzing data structure for optimal visualizations...",
                "content": "📊 Determining best charts with full context",
                "progress": 10
            }
        }
        
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "Finalization",
                "data": {
                    "scope": "Finalization",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for visualization suggestions",
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
                    "error": {"type": "handler_error", "message": "Model handler not set"}
                }
            )

        # Extract comprehensive context from state
        user_question = state.get("input", "")
        data = state.get("execution_results", [])
        query_plan = state.get("query_plan", {})
        query_strategy = state.get("query_strategy", "")
        trends_and_patterns = state.get("trends_and_patterns", [])
        key_insights = state.get("key_insights", [])
        temporal_aspects = query_plan.get("temporal_aspects", {}) if query_plan else {}
        
        # Emit analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": f"Analyzing {len(data)} data points and {len(trends_and_patterns)} trends...",
                "content": f"🔍 Examining {query_strategy} results for visualization",
                "progress": 40
            }
        }
        
        # Emit generation progress
        generation_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Generating optimal visualization recommendations...",
                "content": "🤖 AI suggesting best charts and graphs",
                "progress": 70
            }
        }

        # Create comprehensive visualization prompt
        prompt = f"""
You are a data visualization expert recommending optimal charts and graphs based on comprehensive data analysis results.

USER QUESTION: {user_question}

QUERY STRATEGY: {query_strategy}

DATA STRUCTURE ({len(data)} rows):
Columns: {list(data[0].keys()) if data else []}
Sample Data: {json.dumps(data[:3], indent=2) if data else "No data"}

TEMPORAL ANALYSIS CONTEXT:
{json.dumps(temporal_aspects, indent=2) if temporal_aspects else "No temporal context"}

IDENTIFIED TRENDS AND PATTERNS:
{chr(10).join(trends_and_patterns) if trends_and_patterns else "No trends identified"}

KEY INSIGHTS:
{chr(10).join(key_insights) if key_insights else "No key insights available"}

QUERY PLAN CONTEXT:
{json.dumps(query_plan, indent=2) if query_plan else "No query plan available"}

VISUALIZATION REQUIREMENTS:
1. Recommend specific chart types that best represent the data
2. Consider the data types and relationships
3. Account for temporal aspects if present
4. Align visualizations with the identified trends and patterns
5. Support the key insights with appropriate visual representations
6. Consider the user's original question and how visuals can answer it
7. Provide specific guidance on what data should be plotted
8. Consider interactive elements if beneficial
9. Suggest multiple visualization options for different aspects of the data
10. If no data, suggest what visualizations would be helpful if data were available

Provide detailed visualization recommendations that effectively communicate the analysis findings.
"""
        
        response = await handler.model.ainvoke(prompt)
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Comprehensive visualization suggestions generated",
                "content": "✅ Optimal chart recommendations created",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Comprehensive visualization suggestions generated",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, analysis_progress_event, generation_progress_event, completion_progress_event],
                "visualization_suggestions": response.content.split('\n') if response.content else []
            }
        )    
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": f"Visualization generation failed: {str(e)}",
                "content": "❌ Failed to generate visualization suggestions",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Visualization generation failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "visualization_error", "message": str(e)}
            }
        )


@tool
async def format_final_answer(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Format the final answer using comprehensive analysis context."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Formatting comprehensive final answer...",
                "content": "📋 Creating complete user-friendly report",
                "progress": 10
            }
        }
        
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "Finalization",
                "data": {
                    "scope": "Finalization",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for answer formatting",
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
                    "error": {"type": "handler_error", "message": "Model handler not set"}
                }
            )

        # Extract comprehensive context from state
        user_question = state.get("input", "")
        final_summary = state.get("final_summary", "")
        key_insights = state.get("key_insights", [])
        visualization_suggestions = state.get("visualization_suggestions", [])
        sql_query = state.get("sql_query", "")
        execution_results = state.get("execution_results", [])
        data_summary = state.get("data_summary", "")
        query_strategy = state.get("query_strategy", "")
        zero_result_attempts = state.get("zero_result_attempts", 0)
        
        # Emit formatting progress
        formatting_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": f"Formatting complete analysis with {len(key_insights)} insights...",
                "content": "⚙️ Structuring comprehensive final answer",
                "progress": 50
            }
        }

        # Create comprehensive formatting prompt
        prompt = f"""
You are a senior analyst formatting a comprehensive final answer for a user. Create a well-structured, professional report that is both informative and accessible.

USER QUESTION: {user_question}

ANALYSIS SUMMARY: {final_summary}

KEY INSIGHTS:
{chr(10).join(key_insights) if key_insights else "No key insights available"}

DATA SUMMARY: {data_summary}

QUERY STRATEGY: {query_strategy}

EXECUTED SQL QUERY:
{sql_query}

RESULTS COUNT: {len(execution_results)} rows

VISUALIZATION SUGGESTIONS:
{chr(10).join(visualization_suggestions) if visualization_suggestions else "No visualization suggestions"}

ANALYSIS METADATA:
- Zero result attempts: {zero_result_attempts}
- Query strategy: {query_strategy}

FORMATTING REQUIREMENTS:
1. Create a professional, well-structured markdown report
2. Start with an executive summary that directly answers the user's question
3. Include a methodology section explaining the analysis approach
4. Present key findings with supporting data
5. Include the SQL query used (in a code block)
6. Highlight the most important insights
7. Add visualization recommendations if applicable
8. Include limitations and considerations
9. Provide actionable recommendations where appropriate
10. End with a clear conclusion
11. Use appropriate markdown formatting (headers, lists, code blocks, emphasis)
12. Make it accessible to both technical and non-technical audiences

Create a comprehensive, professional final answer that fully addresses the user's question.
"""
        
        response = await handler.model.ainvoke(prompt)
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Comprehensive final answer formatted",
                "content": "✅ Complete user-friendly report created",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Comprehensive final answer formatted",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, formatting_progress_event, completion_progress_event],
                "final_answer": response.content
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": f"Answer formatting failed: {str(e)}",
                "content": "❌ Failed to format final answer",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Answer formatting failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "formatting_error", "message": str(e)}
            }
        )


@tool
async def generate_follow_up_questions(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Generate relevant follow-up questions based on comprehensive analysis context."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Generating contextual follow-up questions...",
                "content": "❓ Creating relevant questions based on complete analysis",
                "progress": 10
            }
        }
        
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "Finalization",
                "data": {
                    "scope": "Finalization",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for question generation",
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
                    "error": {"type": "handler_error", "message": "Model handler not set"}
                }
            )

        # Extract comprehensive context from state
        user_question = state.get("input", "")
        final_summary = state.get("final_summary", "")
        key_insights = state.get("key_insights", [])
        query_plan = state.get("query_plan", {})
        execution_results = state.get("execution_results", [])
        schema_context = state.get("schema_context", {})
        query_strategy = state.get("query_strategy", "")
        trends_and_patterns = state.get("trends_and_patterns", [])
        
        # Emit analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Analyzing complete context for question opportunities...",
                "content": "🔍 Identifying areas for deeper exploration",
                "progress": 50
            }
        }

        # Create comprehensive follow-up question prompt
        prompt = f"""
You are a senior analyst generating relevant follow-up questions based on a comprehensive data analysis. Create questions that would naturally arise from the findings and provide value to the user.

USER QUESTION: {user_question}

ANALYSIS SUMMARY: {final_summary}

KEY INSIGHTS:
{chr(10).join(key_insights) if key_insights else "No key insights available"}

IDENTIFIED TRENDS AND PATTERNS:
{chr(10).join(trends_and_patterns) if trends_and_patterns else "No trends identified"}

QUERY STRATEGY: {query_strategy}

RESULTS COUNT: {len(execution_results)} rows

QUERY PLAN CONTEXT:
{json.dumps(query_plan, indent=2) if query_plan else "No query plan available"}

AVAILABLE SCHEMA CONTEXT:
{json.dumps(schema_context, indent=2) if schema_context else "No schema context"}

FOLLOW-UP QUESTION REQUIREMENTS:
1. Generate 4-6 relevant follow-up questions
2. Base questions on the actual findings and insights
3. Consider different aspects: deeper analysis, related data, trends, comparisons
4. Include questions that could leverage other data in the schema
5. Suggest questions for different time periods if temporal data is involved
6. Consider questions that would help validate or expand on the findings
7. Include both technical and business-oriented questions
8. Make questions specific and actionable
9. Consider edge cases or exceptions that might be interesting
10. If zero results, suggest questions to understand why or find alternative approaches

Create questions that would provide additional value and insights to the user.
"""
        
        response = await handler.model.ainvoke(prompt)
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": "Contextual follow-up questions generated",
                "content": "✅ Relevant questions created for deeper exploration",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Contextual follow-up questions generated",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, analysis_progress_event, completion_progress_event],
                "follow_up_questions": response.content.split('\n') if response.content else []
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "Finalization",
            "data": {
                "scope": "Finalization",
                "description": f"Question generation failed: {str(e)}",
                "content": "❌ Failed to generate follow-up questions",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Question generation failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "question_error", "message": str(e)}
            }
        )


def finalization_pre_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Pre-model hook for finalization agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "Finalization",
        "data": {
            "scope": "Finalization",
            "description": "Creating comprehensive final summary and formatting results",
            "content": "📝 Starting final summary and report generation"
        }
    }
    return {"agent_lifecycle_events": [event]}


def finalization_post_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Post-model hook for finalization agent - emits agent end event"""
    event = {
        "type": "agent:end",
        "name": "Finalization",
        "data": {
            "scope": "Finalization",
            "description": "Generated final summary and formatted results for user",
            "content": "✅ Completed final report generation and analysis"
        }
    }
    return {"agent_lifecycle_events": [event]} 