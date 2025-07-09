import json
from typing import Any, Dict, Generator
import logging

from langchain_core.messages import AIMessage, ToolMessage, BaseMessage

from doorbeen.core.events.generator import AgentEvent
from doorbeen.core.events.types import EventTypes, EventCategory, EventStage, EventSource


class LangGraphEventProcessor:
    """
    Enhanced processor to handle agent lifecycle events and raw LangGraph events.
    Processes raw event dictionaries from LangGraph's astream method with
    stream_mode="updates" and transforms them into structured AgentEvent objects.
    """

    def __init__(self):
        self._processed_messages_count: Dict[str, int] = {}
        self._processed_events_count: Dict[str, int] = {}  # Track processed lifecycle events
        
        # Mapping from LangGraph node names to event sources
        self._node_to_source_mapping = {
            'supervisor': EventSource.SUPERVISOR,
            'DataAnalyst': EventSource.DATA_ANALYST,
            'QueryGenerator': EventSource.QUERY_GENERATOR,
            'ResultProcessor': EventSource.RESULT_PROCESSOR,
            'Finalizer': EventSource.FINALIZER,
            'ObjectiveEvaluator': EventSource.OBJECTIVE_EVALUATOR,
        }

    def transform_event(self, event: Dict[str, Any]) -> Generator[AgentEvent, None, None]:
        """
        Transforms a single raw LangGraph event into one or more AgentEvents.
        An event from stream_mode="updates" is a dict with one key (the node name)
        and the value is the state update.
        """
        logging.info(f"Processing raw event: {event}")
        for node_name, state_update in event.items():
            if not isinstance(state_update, dict):
                continue
            
            # Debug: Log available fields in state_update
            logging.info(f"[DEBUG] Node: {node_name}, Available fields: {list(state_update.keys())}")
            
            # Handle our custom lifecycle events - only process new ones
            if "agent_lifecycle_events" in state_update and state_update["agent_lifecycle_events"]:
                if node_name not in self._processed_events_count:
                    self._processed_events_count[node_name] = 0
                
                # Only process new events that haven't been streamed yet
                new_events = state_update["agent_lifecycle_events"][self._processed_events_count[node_name]:]
                logging.info(f"[DEBUG] Processing {len(new_events)} new lifecycle events from {node_name} (total: {len(state_update['agent_lifecycle_events'])}, processed: {self._processed_events_count[node_name]})")
                
                for event_data in new_events:
                    # Enhance the event with rich context
                    enhanced_event = self._enhance_lifecycle_event(event_data, node_name)
                    yield enhanced_event
                    logging.info(f"Yielded enhanced agent lifecycle event: {enhanced_event.type}")
                
                # Update the processed count
                self._processed_events_count[node_name] = len(state_update["agent_lifecycle_events"])

            # Handle messages
            if "messages" in state_update:
                if node_name not in self._processed_messages_count:
                    self._processed_messages_count[node_name] = 0
                
                new_messages = state_update["messages"][self._processed_messages_count[node_name]:]
                logging.info(f"[DEBUG] Processing {len(new_messages)} new messages from {node_name}")
                for message in new_messages:
                    if isinstance(message, AIMessage):
                        yield from self._process_ai_message(node_name, message)
                    elif isinstance(message, ToolMessage):
                        yield from self._process_tool_message(node_name, message)
                    else:
                        logging.warning(f"Ignoring message of type {type(message).__name__} from node {node_name}: {message}")

                self._processed_messages_count[node_name] = len(state_update["messages"])

    def _enhance_lifecycle_event(self, event_data: Dict[str, Any], node_name: str) -> AgentEvent:
        """Enhance a lifecycle event with rich context information."""
        
        # Extract basic event information
        event_type = event_data.get("type", "unknown")
        event_name = event_data.get("name", node_name)
        event_content = event_data.get("data", {})
        
        # Determine category based on event type
        category = self._determine_event_category(event_type)
        
        # Determine source based on node name (dictionary key)
        source = self._determine_event_source_from_node(node_name)
        
        # Determine stage based on event data
        stage = self._determine_event_stage(event_content, event_name)
        
        # Create metadata with useful context
        metadata = self._create_event_metadata(event_content, node_name)
        
        return AgentEvent(
            type=event_type,
            name=event_name,
            data=event_content,
            category=category,
            source=source,
            stage=stage,
            metadata=metadata
        )

    def _determine_event_category(self, event_type: str) -> str:
        """Determine the category of an event based on its type."""
        if event_type == EventTypes.AGENT_PROGRESS:
            return EventCategory.PROGRESS
        elif event_type == EventTypes.ERROR or event_type == "agent:error":
            return EventCategory.ERROR
        elif event_type == EventTypes.AGENT_WARNING:
            return EventCategory.WARNING
        elif event_type == EventTypes.AGENT_START or event_type == EventTypes.AGENT_END:
            return EventCategory.LIFECYCLE
        elif event_type == EventTypes.TOOL_INVOKE:
            return EventCategory.TOOL_CALL
        elif event_type == EventTypes.AGENT_HANDOFF:
            return EventCategory.HANDOFF
        elif event_type == EventTypes.SUPERVISOR_ROUTING:
            return EventCategory.SUPERVISOR
        else:
            return EventCategory.AGENT_OUTPUT

    def _determine_event_source_from_node(self, node_name: str) -> str:
        """Determine the source of an event based on the LangGraph node name (dictionary key)."""
        # Use direct mapping from node name to source
        source = self._node_to_source_mapping.get(node_name)
        if source:
            return source
        
        # Fallback to pattern matching for unknown node names
        node_lower = node_name.lower()
        if "supervisor" in node_lower:
            return EventSource.SUPERVISOR
        elif "data" in node_lower or "analyst" in node_lower:
            return EventSource.DATA_ANALYST
        elif "query" in node_lower or "generation" in node_lower:
            return EventSource.QUERY_GENERATOR
        elif "result" in node_lower or "processing" in node_lower:
            return EventSource.RESULT_PROCESSOR
        elif "final" in node_lower:
            return EventSource.FINALIZER
        elif "objective" in node_lower or "evaluation" in node_lower:
            return EventSource.OBJECTIVE_EVALUATOR
        else:
            return EventSource.SYSTEM

    def _determine_event_stage(self, event_content: Dict[str, Any], event_name: str) -> str:
        """Determine the workflow stage based on event content."""
        scope = event_content.get("scope", "").lower()
        description = event_content.get("description", "").lower()
        
        if "schema" in scope or "schema" in description:
            return EventStage.SCHEMA_ANALYSIS
        elif "query" in scope and ("generat" in description or "draft" in description):
            return EventStage.QUERY_GENERATION
        elif "query" in scope and ("validat" in description or "correct" in description):
            return EventStage.QUERY_VALIDATION
        elif "query" in scope and ("execut" in description or "run" in description):
            return EventStage.QUERY_EXECUTION
        elif "result" in scope or "process" in description:
            return EventStage.RESULT_PROCESSING
        elif "final" in scope or "final" in description:
            return EventStage.FINALIZATION
        elif "handoff" in description or "transfer" in description:
            return EventStage.HANDOFF
        elif "error" in description or "fail" in description:
            return EventStage.ERROR_HANDLING
        elif "plan" in description:
            return EventStage.PLANNING
        else:
            return EventStage.INITIALIZATION

    def _create_event_metadata(self, event_content: Dict[str, Any], node_name: str) -> Dict[str, Any]:
        """Create metadata for better UI context."""
        metadata = {
            "node_name": node_name,
            "timestamp": event_content.get("timestamp"),
            "scope": event_content.get("scope"),
            "progress": event_content.get("progress"),
        }
        
        # Add specific metadata based on content
        if "description" in event_content:
            metadata["description"] = event_content["description"]
        
        if "content" in event_content:
            metadata["content"] = event_content["content"]
        
        # Add workflow-specific metadata
        if "workflow_stage" in event_content:
            metadata["workflow_stage"] = event_content["workflow_stage"]
        
        if "attempt" in event_content:
            metadata["attempt"] = event_content["attempt"]
        
        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}

    def _process_ai_message(self, node_name: str, message: AIMessage) -> Generator[AgentEvent, None, None]:
        """Processes an AIMessage, which can contain tool calls or content."""
        if message.tool_calls:
            for tool_call in message.tool_calls:
                agent_event = AgentEvent(
                    type=EventTypes.TOOL_INVOKE.value,
                    name=tool_call.get("name", "UnknownTool"),
                    data=tool_call,
                    category=EventCategory.TOOL_CALL,
                    source=self._determine_event_source_from_node(node_name),
                    stage=EventStage.QUERY_EXECUTION,
                    metadata={"node_name": node_name, "tool_call_id": tool_call.get("id")}
                )
                yield agent_event
                logging.info(f"Yielded tool invoke event: {tool_call.get('name')}")
        elif message.content:
            agent_event = AgentEvent(
                type=EventTypes.STREAM_OUTPUT.value,
                name=node_name,
                data={"content": message.content},
                category=EventCategory.AGENT_OUTPUT,
                source=self._determine_event_source_from_node(node_name),
                stage=EventStage.QUERY_EXECUTION,
                metadata={"node_name": node_name, "content_length": len(message.content)}
            )
            yield agent_event
            logging.info(f"Yielded stream output event from node: {node_name}")
        else:
            logging.warning(f"AIMessage from node {node_name} has no tool_calls or content, ignoring: {message}")

    def _process_tool_message(self, node_name: str, message: ToolMessage) -> Generator[AgentEvent, None, None]:
        """Processes a ToolMessage, which contains the output of a tool."""
        agent_event = AgentEvent(
            type=EventTypes.NODE_OUTPUT.value,
            name=node_name,
            data={
                "tool_call_id": message.tool_call_id,
                "content": message.content,
            },
            category=EventCategory.AGENT_OUTPUT,
            source=self._determine_event_source_from_node(node_name),
            stage=EventStage.QUERY_EXECUTION,
            metadata={
                "node_name": node_name,
                "tool_call_id": message.tool_call_id,
                "content_length": len(message.content) if message.content else 0
            }
        ) 
        yield agent_event
        logging.info(f"Yielded node output event from node: {node_name}") 