from enum import Enum


class EventTypes(str, Enum):
    TOOL_INVOKE = "agent:tool:invoke"
    STREAM_OUTPUT = "agent:stream:output"
    MESSAGE = "agent:message"
    ERROR = "agent:error"
    NODE_OUTPUT = "assistant:node:output"
