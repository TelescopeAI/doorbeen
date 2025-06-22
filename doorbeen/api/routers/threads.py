import json
import logging
import traceback
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Path
from starlette.responses import JSONResponse

from doorbeen.api.schemas.requests.threads import (
    CreateThreadRequest, 
    UpdateThreadRequest, 
    ListThreadsRequest, 
    GetMessagesRequest
)
from doorbeen.api.schemas.responses.threads import (
    ThreadResponse, 
    MessageResponse,
    CreateThreadResponse,
    ListThreadsResponse,
    GetMessagesResponse,
    ThreadSummaryResponse,
    DeleteThreadResponse,
    ErrorResponse
)
from doorbeen.core.storage import StorageManager, StorageConfig

ThreadsRouter = APIRouter()

# Global storage manager instance
_storage_manager = None


async def get_storage_manager() -> StorageManager:
    """Get or create the global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        config = StorageConfig()
        _storage_manager = StorageManager(config)
        await _storage_manager.initialize()
        logging.info("[THREADS] Storage manager initialized")
    return _storage_manager


def thread_to_response(thread) -> ThreadResponse:
    """Convert storage Thread model to ThreadResponse."""
    return ThreadResponse(
        id=thread.id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        metadata=thread.metadata,
        message_count=thread.message_count
    )


def message_to_response(message) -> MessageResponse:
    """Convert storage Message model to MessageResponse."""
    return MessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        content=message.content,
        role=message.role,
        created_at=message.created_at,
        metadata=message.metadata
    )


@ThreadsRouter.post("/threads", 
                   response_model=CreateThreadResponse,
                   tags=["Threads"], 
                   operation_id="create_thread")
async def create_thread(request: CreateThreadRequest):
    """Create a new conversation thread."""
    try:
        logging.info(f"[THREADS] Creating new thread with metadata: {request.metadata}")
        
        storage_manager = await get_storage_manager()
        thread = await storage_manager.create_thread(request.metadata or {})
        
        logging.info(f"[THREADS] Created thread: {thread.id}")
        
        return CreateThreadResponse(
            thread=thread_to_response(thread),
            message="Thread created successfully"
        )
        
    except Exception as e:
        logging.error(f"[THREADS] Error creating thread: {str(e)}")
        logging.error(f"[THREADS] Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create thread: {str(e)}"
        )


@ThreadsRouter.get("/threads", 
                  response_model=ListThreadsResponse,
                  tags=["Threads"], 
                  operation_id="list_threads")
async def list_threads(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of threads to return"),
    offset: int = Query(default=0, ge=0, description="Number of threads to skip")
):
    """List conversation threads with pagination."""
    try:
        logging.info(f"[THREADS] Listing threads with limit={limit}, offset={offset}")
        
        storage_manager = await get_storage_manager()
        threads = await storage_manager.list_threads(limit=limit, offset=offset)
        
        # For total count, we'd need to add a count method to StorageManager
        # For now, we'll estimate based on whether we got a full page
        total_count = offset + len(threads) + (1 if len(threads) == limit else 0)
        has_more = len(threads) == limit
        
        logging.info(f"[THREADS] Retrieved {len(threads)} threads")
        
        return ListThreadsResponse(
            threads=[thread_to_response(thread) for thread in threads],
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_more=has_more
        )
        
    except Exception as e:
        logging.error(f"[THREADS] Error listing threads: {str(e)}")
        logging.error(f"[THREADS] Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list threads: {str(e)}"
        )


@ThreadsRouter.get("/threads/{thread_id}", 
                  response_model=ThreadResponse,
                  tags=["Threads"], 
                  operation_id="get_thread")
async def get_thread(
    thread_id: UUID = Path(..., description="Thread ID")
):
    """Get a specific thread by ID."""
    try:
        logging.info(f"[THREADS] Getting thread: {thread_id}")
        
        storage_manager = await get_storage_manager()
        thread = await storage_manager.get_thread(thread_id)
        
        if thread is None:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {thread_id} not found"
            )
        
        logging.info(f"[THREADS] Retrieved thread: {thread_id}")
        
        return thread_to_response(thread)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[THREADS] Error getting thread {thread_id}: {str(e)}")
        logging.error(f"[THREADS] Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get thread: {str(e)}"
        )


@ThreadsRouter.put("/threads/{thread_id}", 
                  response_model=ThreadResponse,
                  tags=["Threads"], 
                  operation_id="update_thread")
async def update_thread(
    request: UpdateThreadRequest,
    thread_id: UUID = Path(..., description="Thread ID")
):
    """Update thread metadata."""
    try:
        logging.info(f"[THREADS] Updating thread {thread_id} with metadata: {request.metadata}")
        
        storage_manager = await get_storage_manager()
        thread = await storage_manager.update_thread_metadata(thread_id, request.metadata)
        
        if thread is None:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {thread_id} not found"
            )
        
        logging.info(f"[THREADS] Updated thread: {thread_id}")
        
        return thread_to_response(thread)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[THREADS] Error updating thread {thread_id}: {str(e)}")
        logging.error(f"[THREADS] Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update thread: {str(e)}"
        )


@ThreadsRouter.delete("/threads/{thread_id}", 
                     response_model=DeleteThreadResponse,
                     tags=["Threads"], 
                     operation_id="delete_thread")
async def delete_thread(
    thread_id: UUID = Path(..., description="Thread ID")
):
    """Delete a thread and all its messages."""
    try:
        logging.info(f"[THREADS] Deleting thread: {thread_id}")
        
        storage_manager = await get_storage_manager()
        deleted = await storage_manager.delete_thread(thread_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {thread_id} not found"
            )
        
        logging.info(f"[THREADS] Deleted thread: {thread_id}")
        
        return DeleteThreadResponse(
            thread_id=thread_id,
            message="Thread deleted successfully",
            deleted=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[THREADS] Error deleting thread {thread_id}: {str(e)}")
        logging.error(f"[THREADS] Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete thread: {str(e)}"
        )


@ThreadsRouter.get("/threads/{thread_id}/messages", 
                  response_model=GetMessagesResponse,
                  tags=["Threads"], 
                  operation_id="get_thread_messages")
async def get_thread_messages(
    thread_id: UUID = Path(..., description="Thread ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of messages to return"),
    offset: int = Query(default=0, ge=0, description="Number of messages to skip")
):
    """Get messages in a thread with pagination."""
    try:
        logging.info(f"[THREADS] Getting messages for thread {thread_id} with limit={limit}, offset={offset}")
        
        storage_manager = await get_storage_manager()
        
        # First verify the thread exists
        thread = await storage_manager.get_thread(thread_id)
        if thread is None:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {thread_id} not found"
            )
        
        # Get messages
        messages = await storage_manager.get_messages(thread_id, limit=limit, offset=offset)
        total_count = await storage_manager.get_thread_message_count(thread_id)
        
        has_more = offset + len(messages) < total_count
        
        logging.info(f"[THREADS] Retrieved {len(messages)} messages for thread {thread_id}")
        
        return GetMessagesResponse(
            messages=[message_to_response(message) for message in messages],
            thread_id=thread_id,
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[THREADS] Error getting messages for thread {thread_id}: {str(e)}")
        logging.error(f"[THREADS] Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get thread messages: {str(e)}"
        )


@ThreadsRouter.get("/threads/{thread_id}/summary", 
                  response_model=ThreadSummaryResponse,
                  tags=["Threads"], 
                  operation_id="get_thread_summary")
async def get_thread_summary(
    thread_id: UUID = Path(..., description="Thread ID"),
    recent_limit: int = Query(default=10, ge=1, le=50, description="Number of recent messages to include")
):
    """Get thread summary with recent messages."""
    try:
        logging.info(f"[THREADS] Getting summary for thread {thread_id}")
        
        storage_manager = await get_storage_manager()
        
        # Get thread
        thread = await storage_manager.get_thread(thread_id)
        if thread is None:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {thread_id} not found"
            )
        
        # Get recent messages
        recent_messages = await storage_manager.get_messages(thread_id, limit=recent_limit)
        
        # Get first and last messages if any exist
        first_message = None
        last_message = None
        
        if recent_messages:
            all_messages = await storage_manager.get_messages(thread_id, limit=1000)  # Get more for first/last
            if all_messages:
                first_message = all_messages[0]
                last_message = all_messages[-1]
        
        logging.info(f"[THREADS] Retrieved summary for thread {thread_id}")
        
        return ThreadSummaryResponse(
            thread=thread_to_response(thread),
            recent_messages=[message_to_response(msg) for msg in recent_messages],
            first_message=message_to_response(first_message) if first_message else None,
            last_message=message_to_response(last_message) if last_message else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[THREADS] Error getting thread summary {thread_id}: {str(e)}")
        logging.error(f"[THREADS] Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get thread summary: {str(e)}"
        )


@ThreadsRouter.get("/messages/{message_id}/node-events",
                  tags=["Threads"], 
                  operation_id="get_message_node_events")
async def get_message_node_events(
    message_id: UUID = Path(..., description="Assistant message ID")
):
    """Get all node execution events for a specific assistant message."""
    try:
        logging.info(f"[THREADS] Getting node events for message {message_id}")
        
        storage_manager = await get_storage_manager()
        
        # Get the assistant message first to verify it exists
        assistant_message = await storage_manager.get_message(message_id)
        if not assistant_message:
            raise HTTPException(
                status_code=404,
                detail=f"Message {message_id} not found"
            )
        
        if assistant_message.role != "assistant":
            raise HTTPException(
                status_code=400,
                detail="Node events are only available for assistant messages"
            )
        
        # Get all node events for this message
        node_events = await storage_manager.get_node_events_for_message(message_id)
        
        # Parse and structure the node events
        structured_events = []
        for event in node_events:
            try:
                # Parse the stored JSON content
                event_data = json.loads(event.content)
                structured_events.append({
                    "id": str(event.id),
                    "type": event_data.get("type"),
                    "name": event_data.get("name"),
                    "data": event_data.get("data"),
                    "occurred_at": event_data.get("occurred_at"),
                    "stored_at": event.created_at,
                    "metadata": event.metadata
                })
            except json.JSONDecodeError:
                # Skip malformed events
                logging.warning(f"[THREADS] Skipping malformed node event {event.id}")
                continue
        
        logging.info(f"[THREADS] Retrieved {len(structured_events)} node events for message {message_id}")
        
        return {
            "message_id": str(message_id),
            "node_events": structured_events,
            "total_events": len(structured_events),
            "assistant_message": {
                "id": str(assistant_message.id),
                "content": assistant_message.content,
                "created_at": assistant_message.created_at,
                "metadata": assistant_message.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[THREADS] Error getting node events for message {message_id}: {str(e)}")
        logging.error(f"[THREADS] Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get node events: {str(e)}"
        )


async def cleanup_threads_storage():
    """Clean up the global storage manager."""
    global _storage_manager
    if _storage_manager:
        await _storage_manager.shutdown()
        _storage_manager = None
        logging.info("[THREADS] Storage manager cleaned up") 