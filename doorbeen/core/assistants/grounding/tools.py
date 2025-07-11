"""
Grounding tools for finding similar examples and applying guidance.
"""

import json
from typing import List, Dict, Any
from typing_extensions import Annotated

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.assistants.grounding.models import AnalysisExample, GroundingContext


@tool
async def find_similar_examples(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    similarity_threshold: float = 0.7
) -> Command:
    """Find examples similar to the current user question."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "Supervisor",
            "data": {
                "scope": "Grounding",
                "description": "Searching for similar analysis examples...",
                "content": "🔍 Finding relevant examples to guide analysis",
                "progress": 10
            }
        }
        
        configuration = config.get("configurable", {})
        handler: ModelHandler = configuration.get("handler")
        
        if not handler:
            error_event = {
                "type": "agent:error",
                "name": "Supervisor",
                "data": {
                    "scope": "Grounding",
                    "description": "Model handler not available",
                    "content": "❌ No model handler for similarity analysis",
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
                    "agent_lifecycle_events": [start_progress_event, error_event]
                }
            )
        
        user_question = state.get("input", "")
        examples = state.get("past_examples", [])
        
        if not examples:
            no_examples_event = {
                "type": "agent:warning",
                "name": "Supervisor",
                "data": {
                    "scope": "Grounding",
                    "description": "No examples available for similarity analysis",
                    "content": "⚠️ No examples configured",
                    "progress": 100
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No examples available for similarity analysis",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, no_examples_event],
                    "similar_examples": [],
                    "guidance_applied": False
                }
            )
        
        # Emit analysis progress
        analysis_progress_event = {
            "type": "agent:progress",
            "name": "Supervisor",
            "data": {
                "scope": "Grounding",
                "description": f"Analyzing similarity with {len(examples)} examples...",
                "content": "🤖 AI comparing question with examples",
                "progress": 50
            }
        }
        
        # Create similarity analysis prompt
        examples_text = "\n".join([
            f"Example {i+1}: {ex.get('question', '')}"
            for i, ex in enumerate(examples)
        ])
        
        similarity_prompt = f"""
You are analyzing question similarity to find relevant examples for guidance.

USER QUESTION: {user_question}

AVAILABLE EXAMPLES:
{examples_text}

For each example, determine if it's similar to the user question based on:
1. Topic/domain similarity
2. Analysis type similarity  
3. Expected output similarity

Return a JSON object with similarity scores (0-1) for each example:
{{
  "similarities": [
    {{"example_index": 0, "score": 0.8, "reasoning": "Both ask about performance over time"}},
    {{"example_index": 1, "score": 0.2, "reasoning": "Different topic - products vs revenue"}}
  ],
  "threshold": {similarity_threshold}
}}

Only include examples with scores >= {similarity_threshold}.
"""
        
        response = await handler.model.ainvoke(similarity_prompt)
        
        try:
            similarity_result = json.loads(response.content)
            similarities = similarity_result.get("similarities", [])
            
            # Filter similar examples
            similar_examples = []
            for sim in similarities:
                if sim.get("score", 0) >= similarity_threshold:
                    example_index = sim.get("example_index", -1)
                    if 0 <= example_index < len(examples):
                        example = examples[example_index].copy()
                        example["similarity_score"] = sim.get("score", 0)
                        example["similarity_reasoning"] = sim.get("reasoning", "")
                        similar_examples.append(example)
            
            # Sort by similarity score (highest first)
            similar_examples.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            
        except json.JSONDecodeError:
            # Fallback: no similar examples found
            similar_examples = []
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "Supervisor",
            "data": {
                "scope": "Grounding",
                "description": f"Found {len(similar_examples)} similar examples",
                "content": f"✅ Identified {len(similar_examples)} relevant examples for guidance",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Found {len(similar_examples)} similar examples for guidance",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, analysis_progress_event, completion_progress_event],
                "similar_examples": similar_examples,
                "guidance_applied": False
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "Supervisor",
            "data": {
                "scope": "Grounding",
                "description": f"Similarity analysis failed: {str(e)}",
                "content": f"❌ Failed to find similar examples: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Similarity analysis failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "similarity_analysis_error", "message": str(e)}
            }
        )


@tool
async def apply_example_guidance(
    config: Annotated[RunnableConfig, "Configuration"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Apply guidance from similar examples to the current analysis."""
    
    try:
        # Emit initial progress event
        start_progress_event = {
            "type": "agent:progress",
            "name": "Supervisor",
            "data": {
                "scope": "Grounding",
                "description": "Applying example guidance to analysis...",
                "content": "🎯 Customizing analysis based on examples",
                "progress": 10
            }
        }
        
        similar_examples = state.get("similar_examples", [])
        
        if not similar_examples:
            no_guidance_event = {
                "type": "agent:warning",
                "name": "Supervisor",
                "data": {
                    "scope": "Grounding",
                    "description": "No similar examples available for guidance",
                    "content": "⚠️ No guidance examples to apply",
                    "progress": 100
                }
            }
            
            tool_message = ToolMessage(
                content="⚠️ No similar examples available for guidance",
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "agent_lifecycle_events": [start_progress_event, no_guidance_event],
                    "guidance_applied": False
                }
            )
        
        # Emit processing progress
        processing_progress_event = {
            "type": "agent:progress",
            "name": "Supervisor",
            "data": {
                "scope": "Grounding",
                "description": f"Processing guidance from {len(similar_examples)} examples...",
                "content": "⚙️ Extracting instructions and expected output patterns",
                "progress": 50
            }
        }
        
        # Extract guidance from similar examples
        guidance_instructions = []
        expected_output_patterns = []
        
        for example in similar_examples:
            instructions = example.get("instructions", "")
            expected_output = example.get("expected_output", "")
            similarity_score = example.get("similarity_score", 0)
            
            if instructions:
                guidance_instructions.append({
                    "instruction": instructions,
                    "similarity": similarity_score,
                    "source_question": example.get("question", "")
                })
            
            if expected_output:
                expected_output_patterns.append({
                    "pattern": expected_output,
                    "similarity": similarity_score,
                    "source_question": example.get("question", "")
                })
        
        # Emit completion progress
        completion_progress_event = {
            "type": "agent:progress",
            "name": "Supervisor",
            "data": {
                "scope": "Grounding",
                "description": f"Applied guidance from {len(similar_examples)} examples",
                "content": f"✅ Extracted {len(guidance_instructions)} instructions and {len(expected_output_patterns)} output patterns",
                "progress": 100
            }
        }
        
        tool_message = ToolMessage(
            content=f"✅ Applied guidance from {len(similar_examples)} examples",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [start_progress_event, processing_progress_event, completion_progress_event],
                "guidance_instructions": guidance_instructions,
                "expected_output_patterns": expected_output_patterns,
                "guidance_applied": True
            }
        )
        
    except Exception as e:
        error_event = {
            "type": "agent:error",
            "name": "Supervisor",
            "data": {
                "scope": "Grounding",
                "description": f"Guidance application failed: {str(e)}",
                "content": f"❌ Failed to apply guidance: {str(e)}",
                "progress": 0
            }
        }
        
        tool_message = ToolMessage(
            content=f"❌ Guidance application failed: {str(e)}",
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "agent_lifecycle_events": [error_event],
                "error": {"type": "guidance_application_error", "message": str(e)}
            }
        ) 