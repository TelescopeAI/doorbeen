from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.events.types import EventTypes


class AgentEventData(TSModel):
    """Data structure for agent lifecycle events"""
    agent_name: str
    scope: str  # e.g., "DataAnalysis", "QueryGeneration"
    description: str
    event_type: EventTypes  # "start", "working", "end"
    tools: Optional[List[Dict[str, Any]]] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentLifecycleEvent(TSModel):
    """Structured event for agent lifecycle tracking"""
    name: str = "node:output"
    scope: str
    type: str = "agent"
    description: str
    tools: Optional[List[Dict[str, Any]]] = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.utcnow()) 