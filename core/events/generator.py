from datetime import datetime
from typing import Any, Union

from langchain_core.messages import AIMessage
from pydantic import Field

from core.agents.tools.parsers.chunk import ToolInvocation, StreamOutput
from core.events.types import EventTypes
from core.types.outputs import NodeExecutionOutput
from core.types.ts_model import TSModel


class AgentEvent(TSModel):
    type: EventTypes
    name: str
    data: Any
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class AgentEventGenerator(TSModel):
    chunk: Union[ToolInvocation, StreamOutput, NodeExecutionOutput]

    def process_chunk(self) -> AgentEvent:
        event_type = self._determine_event_type()
        assert event_type is not None, "Event type could not be determined"
        data = self._extract_data()
        event_name = self.chunk.name
        event = AgentEvent(
            type=event_type.value,
            name=event_name,
            data=data
        )

        return event

    def _determine_event_type(self) -> EventTypes:
        # Logic to determine event type based on chunk content
        if isinstance(self.chunk, ToolInvocation):
            return EventTypes.TOOL_INVOKE
        elif isinstance(self.chunk, StreamOutput):
            return EventTypes.STREAM_OUTPUT
        elif isinstance(self.chunk, NodeExecutionOutput):
            return EventTypes.NODE_OUTPUT


    def _extract_data(self) -> Any:
        if isinstance(self.chunk, NodeExecutionOutput):
            return self.chunk.value
        return self.chunk.model_dump()
