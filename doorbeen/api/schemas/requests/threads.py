from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import Field

from doorbeen.core.types.ts_model import TSModel


class CreateThreadRequest(TSModel):
    """Request schema for creating a new thread."""
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata for the thread"
    )


class UpdateThreadRequest(TSModel):
    """Request schema for updating thread metadata."""
    metadata: Dict[str, Any] = Field(
        ...,
        description="New metadata for the thread"
    )


class ListThreadsRequest(TSModel):
    """Request schema for listing threads with pagination."""
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of threads to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of threads to skip"
    )


class GetMessagesRequest(TSModel):
    """Request schema for getting messages in a thread."""
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of messages to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of messages to skip"
    ) 