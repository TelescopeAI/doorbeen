import json
from typing import Any, Dict, Generator
import logging

from langchain_core.messages import AIMessage, ToolMessage, BaseMessage

from doorbeen.core.events.generator import AgentEvent
from doorbeen.core.events.types import EventTypes


class LangGraphEventProcessor:
    """
    Enhanced processor to handle agent lifecycle events and raw LangGraph events.
    Processes raw event dictionaries from LangGraph's astream method with
    stream_mode="updates" and transforms them into structured AgentEvent objects.
    """

    def __init__(self):
        self._processed_messages_count: Dict[str, int] = {}

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
            
            # Handle our custom lifecycle events
            if "agent_events" in state_update and state_update["agent_events"]:
                for event_data in state_update["agent_events"]:
                    yield AgentEvent(**event_data)
                    logging.info(f"Yielded agent lifecycle event: {event_data.get('type')}")

            # Handle messages
            if "messages" in state_update:
                if node_name not in self._processed_messages_count:
                    self._processed_messages_count[node_name] = 0
                
                new_messages = state_update["messages"][self._processed_messages_count[node_name]:]
                for message in new_messages:
                    if isinstance(message, AIMessage):
                        yield from self._process_ai_message(node_name, message)
                    elif isinstance(message, ToolMessage):
                        yield from self._process_tool_message(node_name, message)
                    else:
                        logging.warning(f"Ignoring message of type {type(message).__name__} from node {node_name}: {message}")

                self._processed_messages_count[node_name] = len(state_update["messages"])

    def _process_ai_message(self, node_name: str, message: AIMessage) -> Generator[AgentEvent, None, None]:
        """Processes an AIMessage, which can contain tool calls or content."""
        if message.tool_calls:
            for tool_call in message.tool_calls:
                agent_event = AgentEvent(
                    type=EventTypes.TOOL_INVOKE.value,
                    name=tool_call.get("name", "UnknownTool"),
                    data=tool_call,
                )
                yield agent_event
                logging.info(f"Yielded tool invoke event: {tool_call.get('name')}")
        elif message.content:
            agent_event = AgentEvent(
                type=EventTypes.STREAM_OUTPUT.value,
                name=node_name,
                data={"content": message.content},
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
        )
        yield agent_event
        logging.info(f"Yielded node output event from node: {node_name}") 