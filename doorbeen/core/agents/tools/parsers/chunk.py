from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, AsyncGenerator, Optional, Union, AsyncIterator

from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.agents import AgentStep
from langchain_core.runnables import AddableDict
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel


class ResponseState(str, Enum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    OUTPUT = "output"


class ToolRequest(TSModel):
    name: str
    input: Dict[str, Any] = Field(default_factory=dict)


class ToolInvocation(TSModel):
    call: Optional[ToolRequest] = None
    result: Any = None
    invocation_completed: bool = False


class StreamChunk(TSModel):
    content: Dict[str, Any]
    timestamp: datetime


class StreamOutput(TSModel):
    output: str
    streaming_complete: bool = False


class StreamChunkProcessorState(TSModel):
    current_action: Optional[ResponseState] = None
    last_action: Optional[ResponseState] = None
    last_invoke: Optional[ToolInvocation] = None
    invocation_completed: bool = False
    invocations: List[ToolInvocation] = Field(default_factory=list)
    parsed_stream: List[Any] = Field(default_factory=list)
    raw_stream: List[StreamChunk] = Field(default_factory=list)


class StreamChunkProcessor(TSModel):
    state: StreamChunkProcessorState = Field(default_factory=StreamChunkProcessorState)

    async def process_stream(self, agent_stream: AsyncIterator[AddableDict]) -> AsyncGenerator[Dict[str, Any], None]:
        async for chunk in agent_stream:
            self.state.raw_stream.append(StreamChunk(content=chunk, timestamp=datetime.now()))
            parsed_chunk = await self.parse(chunk)
            if isinstance(parsed_chunk, StreamOutput) or parsed_chunk.invocation_completed:
                yield parsed_chunk

    async def parse(self, value: Dict[str, Any]) -> Union[ToolInvocation, StreamOutput]:
        message_obj = value

        message_mode = self.get_message_mode(message_obj)
        is_last_action_call = self.state.last_action == ResponseState.TOOL_CALL
        is_last_action_result = self.state.last_action == ResponseState.TOOL_RESULT
        is_last_action_output = self.state.last_action == ResponseState.OUTPUT
        flush_result = message_mode == ResponseState.TOOL_RESULT and is_last_action_call
        update_output = message_mode == ResponseState.OUTPUT and is_last_action_output

        tool_invoke = ToolInvocation()
        tool_or_output_result = None
        self.state.current_action = message_mode
        if message_mode == ResponseState.TOOL_CALL:
            agent_action: ToolAgentAction = message_obj["actions"][0]
            tc = ToolRequest(name=agent_action.tool, input=agent_action.tool_input)
            tc_invoke = ToolInvocation(call=tc)
            tc_invoke.invocation_completed = False
            self.state.invocation_completed = False
            self.state.invocations.append(tc_invoke)
            self.state.parsed_stream.append(tc_invoke)
            tool_or_output_result = tc_invoke
        elif flush_result:
            agent_step: AgentStep = message_obj["steps"][0]
            first_invocation = len(self.state.invocations) == 1
            flush_index = 0 if first_invocation else len(self.state.invocations) - 1
            self.state.invocations[flush_index].result = agent_step.observation
            self.state.parsed_stream[flush_index] = self.state.invocations[flush_index]
            self.state.invocations[flush_index].invocation_completed = True
            self.state.invocation_completed = True
            tool_or_output_result = self.state.invocations[flush_index]
        elif is_last_action_result and message_mode == ResponseState.OUTPUT:
            stream_output = StreamOutput(output=message_obj["output"])
            stream_output.streaming_complete = True
            self.state.parsed_stream.append(stream_output)
            tool_or_output_result = stream_output
        elif update_output:
            last_index = len(self.state.parsed_stream) - 1
            self.state.parsed_stream[last_index] = message_obj
            tool_or_output_result = {"output": message_obj["output"]}

        self.state.last_action = message_mode
        self.state.last_invoke = tool_or_output_result
        return tool_or_output_result

    def get_message_mode(self, tool_obj: Dict[str, Any]) -> Optional[ResponseState]:
        # Check if the dictionary contains a key with non null values for the given key
        is_steps_present = "steps" in tool_obj
        is_actions_present = "actions" in tool_obj
        is_output_present = "output" in tool_obj
        is_tool_call = is_actions_present and isinstance(tool_obj["actions"][0], ToolAgentAction)
        is_tool_result = is_steps_present and isinstance(tool_obj["steps"][0], AgentStep)

        if is_tool_call:
            return ResponseState.TOOL_CALL
        elif is_tool_result:
            return ResponseState.TOOL_RESULT
        elif is_output_present:
            return ResponseState.OUTPUT
        else:
            return None

    def clear(self):
        self.state = StreamChunkProcessorState()
