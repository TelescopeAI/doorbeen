from enum import Enum


class EventTypes(str, Enum):
    TOOL_INVOKE = "agent:tool:invoke"
    STREAM_OUTPUT = "agent:stream:output"
    MESSAGE = "agent:message"
    ERROR = "agent:error"
    NODE_OUTPUT = "assistant:node:output"
    # NEW AGENT LIFECYCLE EVENT TYPES
    AGENT_START = "agent:start"
    AGENT_WORKING = "agent:working"
    AGENT_END = "agent:end"
