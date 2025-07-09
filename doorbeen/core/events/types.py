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
    AGENT_PROGRESS = "agent:progress"
    AGENT_WARNING = "agent:warning"
    # HANDOFF AND COORDINATION
    AGENT_HANDOFF = "agent:handoff"
    SUPERVISOR_ROUTING = "supervisor:routing"


class EventCategory(str, Enum):
    """Categories for better UI handling"""
    TOOL_CALL = "tool_call"
    AGENT_OUTPUT = "agent_output"
    HANDOFF = "handoff"
    PROGRESS = "progress"
    ERROR = "error"
    WARNING = "warning"
    SUPERVISOR = "supervisor"
    LIFECYCLE = "lifecycle"


class EventStage(str, Enum):
    """Stages of the analysis workflow"""
    INITIALIZATION = "initialization"
    PLANNING = "planning"
    SCHEMA_ANALYSIS = "schema_analysis"
    QUERY_GENERATION = "query_generation"
    QUERY_VALIDATION = "query_validation"
    QUERY_EXECUTION = "query_execution"
    RESULT_PROCESSING = "result_processing"
    FINALIZATION = "finalization"
    HANDOFF = "handoff"
    ERROR_HANDLING = "error_handling"


class EventSource(str, Enum):
    """Sources of events for better tracking"""
    SUPERVISOR = "supervisor"
    DATA_ANALYST = "data_analyst"
    QUERY_GENERATOR = "query_generator"
    RESULT_PROCESSOR = "result_processor"
    FINALIZER = "finalizer"
    OBJECTIVE_EVALUATOR = "objective_evaluator"
    SYSTEM = "system"
