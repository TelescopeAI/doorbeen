from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import Field

from doorbeen.core.types.ts_model import TSModel


class ThreadResponse(TSModel):
    """Response schema for a single thread."""
    id: UUID = Field(..., description="Thread ID")
    created_at: datetime = Field(..., description="Thread creation timestamp")
    updated_at: datetime = Field(..., description="Thread last update timestamp")
    metadata: Dict[str, Any] = Field(..., description="Thread metadata")
    message_count: int = Field(..., description="Number of messages in the thread")


class MessageResponse(TSModel):
    """Response schema for a single message."""
    id: UUID = Field(..., description="Message ID")
    thread_id: UUID = Field(..., description="Thread ID this message belongs to")
    content: str = Field(..., description="Message content")
    role: str = Field(..., description="Message role (user, assistant, system, tool)")
    created_at: datetime = Field(..., description="Message creation timestamp")
    metadata: Dict[str, Any] = Field(..., description="Message metadata")


class CreateThreadResponse(TSModel):
    """Response schema for creating a thread."""
    thread: ThreadResponse = Field(..., description="Created thread information")
    message: str = Field(default="Thread created successfully", description="Success message")


class ListThreadsResponse(TSModel):
    """Response schema for listing threads."""
    threads: List[ThreadResponse] = Field(..., description="List of threads")
    total_count: int = Field(..., description="Total number of threads available")
    limit: int = Field(..., description="Limit used for this request")
    offset: int = Field(..., description="Offset used for this request")
    has_more: bool = Field(..., description="Whether there are more threads available")


class GetMessagesResponse(TSModel):
    """Response schema for getting messages in a thread."""
    messages: List[MessageResponse] = Field(..., description="List of messages")
    thread_id: UUID = Field(..., description="Thread ID")
    total_count: int = Field(..., description="Total number of messages in the thread")
    limit: int = Field(..., description="Limit used for this request")
    offset: int = Field(..., description="Offset used for this request")
    has_more: bool = Field(..., description="Whether there are more messages available")


class ThreadSummaryResponse(TSModel):
    """Response schema for thread summary information."""
    thread: ThreadResponse = Field(..., description="Thread information")
    recent_messages: List[MessageResponse] = Field(..., description="Recent messages in the thread")
    first_message: MessageResponse = Field(None, description="First message in the thread")
    last_message: MessageResponse = Field(None, description="Last message in the thread")


class DeleteThreadResponse(TSModel):
    """Response schema for deleting a thread."""
    thread_id: UUID = Field(..., description="ID of the deleted thread")
    message: str = Field(default="Thread deleted successfully", description="Success message")
    deleted: bool = Field(default=True, description="Whether the thread was successfully deleted")


class ErrorResponse(TSModel):
    """Response schema for error cases."""
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    thread_id: UUID = Field(None, description="Thread ID if applicable")
    status: str = Field(default="error", description="Status indicator") 