import json
from typing_extensions import Annotated

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from doorbeen.core.models.provider import ModelHandler


@tool
async def evaluate_objective_completion(
    summary: str, 
    state: Annotated[dict, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Evaluate if the original objective has been met."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Evaluating objective completion...",
                "content": "🎯 Assessing if analysis meets original objective",
                "progress": 10
            }
            }
        
        # Automatically get objective from state.input
        objective = state["input"]
        
                # Get handler from config
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "ObjectiveEvaluation",
                "data": {
                    "scope": "ObjectiveEvaluation",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for objective evaluation",
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
        
        # Emit analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Analyzing objective against summary...",
                "content": "📊 Comparing objective with analysis results",
                "progress": 50
            }
        }

        prompt = f"""
    Given the user's objective and the summary of the findings, determine if the objective has been fully met.

    Objective: {objective}
    Summary: {summary}

    Respond with "true" if the objective is met, and "false" otherwise, followed by a brief justification.
    """
        
        response = await handler.model.ainvoke(prompt)
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Objective evaluation completed",
                "content": "✅ Determined objective completion status",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Objective evaluation completed",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, analysis_progress_event, completion_progress_event],
                "objective_evaluation": response.content
            }
        ) 
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": f"Objective evaluation failed: {str(e)}",
                "content": "❌ Failed to evaluate objective completion",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Objective evaluation failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "evaluation_error", "message": str(e)}
            }
        )


@tool
async def suggest_next_steps(
    summary: str, 
    state: Annotated[dict, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """If the objective is not met, suggest the next steps."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Generating next steps suggestions...",
                "content": "🔄 Identifying next actions to complete objective",
                "progress": 10
            }
        }
        
        # Automatically get objective from state.input
        objective = state["input"]
        
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
                    error_event = {
                        "type": "agent:error",
                        "name": "ObjectiveEvaluation",
                        "data": {
                            "scope": "ObjectiveEvaluation",
                            "description": "Model handler not available",
                            "content": "❌ No model handler for next steps generation",
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
                
            # Emit analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Analyzing gaps and opportunities...",
                "content": "🔍 Identifying areas needing further analysis",
                "progress": 50
            }
        }

        prompt = f"""
    The user's objective has not yet been fully met. Based on the objective and the summary of findings so far, what are the next logical steps to take?

    Objective: {objective}
    Summary: {summary}

    Suggest a list of concrete next steps.
    """
                
        response = await handler.model.ainvoke(prompt)
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Next steps suggestions generated",
                "content": "✅ Identified actionable next steps",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Next steps suggestions generated",
            tool_call_id=tool_call_id
        )
        
        return Command(
        update={
            "messages": [tool_message],
            "agent_lifecycle_events": [start_progress_event, analysis_progress_event, completion_progress_event],
            "next_steps": response.content.split('\n')
        }
    )
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": f"Next steps generation failed: {str(e)}",
                "content": "❌ Failed to generate next steps",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Next steps generation failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "next_steps_error", "message": str(e)}
            }
        )


@tool
async def check_completeness(
    analysis: str, 
    state: Annotated[dict, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Evaluate if the analysis completely answers the original question."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Checking analysis completeness...",
                "content": "📋 Verifying if analysis answers original question",
                "progress": 10
            }
        }
        
        # Automatically get question from state.input
        question = state["input"]
        
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
                    error_event = {
                        "type": "agent:error",
                        "name": "ObjectiveEvaluation",
                        "data": {
                            "scope": "ObjectiveEvaluation",
                            "description": "Model handler not available",
                            "content": "❌ No model handler for completeness check",
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
                
            # Emit analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Evaluating analysis completeness...",
                "content": "🔍 Checking if all aspects of question are addressed",
                "progress": 50
            }
        }

        prompt = f"""
    Original question: {question}
    Analysis: {analysis}

    Does this analysis completely answer the original question? Answer yes or no and provide reasoning.
    """
            
        response = await handler.model.ainvoke(prompt)
        completeness = "yes" in response.content.lower()
            
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Completeness check completed",
                "content": f"✅ Analysis is {'complete' if completeness else 'incomplete'}",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Completeness check completed - {'Complete' if completeness else 'Incomplete'}",
            tool_call_id=tool_call_id
        )
        
        return Command(
        update={
            "messages": [tool_message],
            "agent_lifecycle_events": [start_progress_event, analysis_progress_event, completion_progress_event],
            "is_complete": completeness,
            "completeness_explanation": response.content
        }
    )
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": f"Completeness check failed: {str(e)}",
                "content": "❌ Failed to check analysis completeness",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Completeness check failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "completeness_error", "message": str(e)}
            }
        )


@tool
async def check_constraints(
    analysis: str, 
    state: Annotated[dict, InjectedState],
    config: Annotated[RunnableConfig, "Configuration"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Check if any constraints mentioned in the original question have been addressed in the analysis."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Checking constraint compliance...",
                "content": "🔒 Verifying constraints are addressed",
                "progress": 10
            }
        }
        
        # Automatically get question from state.input
        question = state["input"]
        
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
                    error_event = {
                        "type": "agent:error",
                        "name": "ObjectiveEvaluation",
                        "data": {
                            "scope": "ObjectiveEvaluation",
                            "description": "Model handler not available",
                            "content": "❌ No model handler for constraint check",
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
                
                # Emit analysis progress
        analysis_progress_event = {
                "type": "agent:progress",
                "name": "ObjectiveEvaluation",
                "data": {
                    "scope": "ObjectiveEvaluation",
                    "description": "Analyzing constraint adherence...",
                    "content": "🔍 Checking if specific requirements are met",
                    "progress": 50
                }
            }

        prompt = f"""
    Original question: {question}
    Analysis: {analysis}

    Are there any constraints or specific requirements in the question that have been addressed in the analysis?
    """
            
        response = await handler.model.ainvoke(prompt)
    
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": "Constraint check completed",
                "content": "✅ Constraint compliance verified",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content="✅ Constraint check completed",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, analysis_progress_event, completion_progress_event],
                "constraints_check": response.content
            }
        )
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "ObjectiveEvaluation",
            "data": {
                "scope": "ObjectiveEvaluation",
                "description": f"Constraint check failed: {str(e)}",
                "content": "❌ Failed to check constraints",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Constraint check failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "constraint_error", "message": str(e)}
            }
        )


def objective_evaluation_pre_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Pre-model hook for objective evaluation agent - emits agent start event"""
    event = {
        "type": "agent:start",
        "name": "ObjectiveEvaluation",
        "data": {
            "scope": "ObjectiveEvaluation",
            "description": "Evaluating if analysis meets the original objective",
            "content": "🎯 Starting objective evaluation and completeness check"
        }
    }
    return {"agent_lifecycle_events": [event]}


def objective_evaluation_post_hook(state: Annotated[dict, InjectedState]) -> dict:
    """Post-model hook for objective evaluation agent - emits agent end event with contextual information"""
    # Extract relevant information from state
    is_complete = state.get("is_complete", False)
    completeness_explanation = state.get("completeness_explanation", "")
    constraints_check = state.get("constraints_check", "")
    objective_evaluation = state.get("objective_evaluation", {})
    
    # Build contextual content
    content_parts = ["🎯 Objective Evaluation Complete"]
    
    # Add completion status
    completion_status = "✅ Complete" if is_complete else "⚠️ Needs attention"
    content_parts.append(f"\n**Status:** {completion_status}")
    
    # Add completeness explanation summary
    if completeness_explanation:
        explanation_preview = completeness_explanation[:120] + "..." if len(completeness_explanation) > 120 else completeness_explanation
        content_parts.append(f"**Assessment:** {explanation_preview}")
    
    # Add constraints check result
    if constraints_check:
        constraints_preview = constraints_check[:100] + "..." if len(constraints_check) > 100 else constraints_check
        content_parts.append(f"\n**Constraints:** {constraints_preview}")
    
    # Add objective evaluation details if available
    if objective_evaluation:
        if isinstance(objective_evaluation, dict):
            if "score" in objective_evaluation:
                content_parts.append(f"**Objective Score:** {objective_evaluation['score']}")
            if "summary" in objective_evaluation:
                summary_preview = objective_evaluation["summary"][:100] + "..." if len(objective_evaluation["summary"]) > 100 else objective_evaluation["summary"]
                content_parts.append(f"**Evaluation:** {summary_preview}")
    
    event = {
        "type": "agent:end",
        "name": "ObjectiveEvaluation",
        "data": {
            "scope": "ObjectiveEvaluation",
            "description": "Assessed objective completion and identified next steps",
            "content": "\n".join(content_parts)
        }
    }
    return {"agent_lifecycle_events": [event]} 