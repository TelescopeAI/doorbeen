import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy import create_engine, select, desc, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from doorbeen.core.storage.config import StorageConfig
from doorbeen.core.storage.models import Base, Thread, ThreadModel, Message, MessageModel


class StorageManager:
    """Async storage manager for thread and message operations."""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the storage manager and create database tables."""
        if self._initialized:
            return
            
        storage_config = self.config.get_storage_config()
        
        # Create async engine
        self.engine = create_async_engine(
            storage_config["url"],
            pool_size=storage_config["pool_size"],
            max_overflow=storage_config["max_overflow"],
            echo=storage_config["echo"]
        )
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self._initialized = True
        logging.info("Storage manager initialized successfully")
    
    async def shutdown(self) -> None:
        """Shutdown the storage manager and clean up resources."""
        if self.engine:
            await self.engine.dispose()
        self._initialized = False
        logging.info("Storage manager shutdown completed")
    
    def _ensure_initialized(self) -> None:
        """Ensure the storage manager is initialized."""
        if not self._initialized:
            raise RuntimeError("StorageManager not initialized. Call initialize() first.")
    
    # Thread operations
    async def create_thread(self, metadata: Dict[str, Any] = None) -> Thread:
        """Create a new conversation thread."""
        self._ensure_initialized()
        
        if metadata is None:
            metadata = {}
        
        async with self.session_factory() as session:
            thread_model = ThreadModel(
                id=uuid4(),
                thread_metadata=json.dumps(metadata) if metadata else '{}'
            )
            
            session.add(thread_model)
            await session.commit()
            await session.refresh(thread_model)
            
            thread = Thread.from_model(thread_model)
            thread.message_count = 0  # New thread has no messages
            return thread
    
    async def get_thread(self, thread_id: UUID, include_messages: bool = False) -> Optional[Thread]:
        """Get a thread by ID."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            query = select(ThreadModel).where(ThreadModel.id == thread_id)
            
            if include_messages:
                query = query.options(selectinload(ThreadModel.messages))
            
            result = await session.execute(query)
            thread_model = result.scalar_one_or_none()
            
            if thread_model is None:
                return None
            
            thread = Thread.from_model(thread_model)
            # Get actual message count
            thread.message_count = await self.get_thread_message_count(thread_id)
            return thread
    
    async def list_threads(self, limit: int = 50, offset: int = 0) -> List[Thread]:
        """List threads with pagination."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            query = (
                select(ThreadModel)
                .order_by(desc(ThreadModel.updated_at))
                .offset(offset)
                .limit(limit)
            )
            
            result = await session.execute(query)
            thread_models = result.scalars().all()
            
            threads = []
            for model in thread_models:
                # Get message count first, then create Thread with proper count
                message_count = await self.get_thread_message_count(model.id)
                thread = Thread.from_model(model)
                thread.message_count = message_count
                threads.append(thread)
            
            return threads
    
    async def update_thread_metadata(self, thread_id: UUID, metadata: Dict[str, Any]) -> Optional[Thread]:
        """Update thread metadata."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            query = select(ThreadModel).where(ThreadModel.id == thread_id)
            result = await session.execute(query)
            thread_model = result.scalar_one_or_none()
            
            if thread_model is None:
                return None
            
            thread_model.thread_metadata = json.dumps(metadata)
            thread_model.updated_at = datetime.now(timezone.utc)
            
            await session.commit()
            await session.refresh(thread_model)
            
            thread = Thread.from_model(thread_model)
            thread.message_count = await self.get_thread_message_count(thread_id)
            return thread
    
    async def delete_thread(self, thread_id: UUID) -> bool:
        """Delete a thread and all its messages."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            query = select(ThreadModel).where(ThreadModel.id == thread_id)
            result = await session.execute(query)
            thread_model = result.scalar_one_or_none()
            
            if thread_model is None:
                return False
            
            await session.delete(thread_model)
            await session.commit()
            
            return True
    
    # Message operations
    async def create_message(
        self, 
        thread_id: UUID, 
        content: str, 
        role: str, 
        metadata: Dict[str, Any] = None
    ) -> Message:
        """Create a new message in a thread."""
        self._ensure_initialized()
        
        if metadata is None:
            metadata = {}
        
        async with self.session_factory() as session:
            message_model = MessageModel(
                id=uuid4(),
                thread_id=thread_id,
                content=content,
                role=role,
                message_metadata=json.dumps(metadata) if metadata else '{}'
            )
            
            session.add(message_model)
            
            # Update thread's updated_at timestamp
            thread_query = select(ThreadModel).where(ThreadModel.id == thread_id)
            thread_result = await session.execute(thread_query)
            thread_model = thread_result.scalar_one_or_none()
            
            if thread_model:
                thread_model.updated_at = datetime.now(timezone.utc)
            
            await session.commit()
            await session.refresh(message_model)
            
            return Message.from_model(message_model)
    
    async def get_messages(self, thread_id: UUID, limit: int = 100, offset: int = 0) -> List[Message]:
        """Get messages for a thread with pagination."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            query = (
                select(MessageModel)
                .where(MessageModel.thread_id == thread_id)
                .order_by(MessageModel.created_at)
                .offset(offset)
                .limit(limit)
            )
            
            result = await session.execute(query)
            message_models = result.scalars().all()
            
            return [Message.from_model(model) for model in message_models]
    
    async def get_message(self, message_id: UUID) -> Optional[Message]:
        """Get a specific message by ID."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            query = select(MessageModel).where(MessageModel.id == message_id)
            result = await session.execute(query)
            message_model = result.scalar_one_or_none()
            
            if message_model is None:
                return None
            
            return Message.from_model(message_model)
    
    async def get_thread_message_count(self, thread_id: UUID) -> int:
        """Get the number of messages in a thread."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            query = select(func.count(MessageModel.id)).where(MessageModel.thread_id == thread_id)
            result = await session.execute(query)
            count = result.scalar()
            
            return count or 0
    
    async def get_node_events_for_message(self, assistant_message_id: UUID) -> List[Message]:
        """Get all node execution events for a specific assistant message."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            query = (
                select(MessageModel)
                .where(
                    MessageModel.role == "node_event",
                    MessageModel.message_metadata.contains(f'"assistant_message_id": "{str(assistant_message_id)}"')
                )
                .order_by(MessageModel.created_at)
            )
            
            result = await session.execute(query)
            node_event_models = result.scalars().all()
            
            return [Message.from_model(model) for model in node_event_models] 
    
    async def get_agent_events_for_message(self, assistant_message_id: UUID) -> List[Message]:
        """Get all agent lifecycle events for a specific assistant message."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            # Get all agent lifecycle events, supervisor events, and assistant events
            query = (
                select(MessageModel)
                .where(
                    MessageModel.role.in_(["agent_lifecycle_event", "supervisor_event", "assistant_event"]),
                    MessageModel.message_metadata.contains(f'"assistant_message_id": "{str(assistant_message_id)}"')
                )
                .order_by(MessageModel.created_at)
            )
            
            result = await session.execute(query)
            agent_event_models = result.scalars().all()
            
            return [Message.from_model(model) for model in agent_event_models]
    
    async def get_all_events_for_message(self, assistant_message_id: UUID) -> List[Message]:
        """Get all events (node events and agent lifecycle events) for a specific assistant message."""
        self._ensure_initialized()
        
        async with self.session_factory() as session:
            # Get all types of events related to this assistant message
            query = (
                select(MessageModel)
                .where(
                    MessageModel.role.in_(["node_event", "agent_lifecycle_event", "supervisor_event", "assistant_event"]),
                    MessageModel.message_metadata.contains(f'"assistant_message_id": "{str(assistant_message_id)}"')
                )
                .order_by(MessageModel.created_at)
            )
            
            result = await session.execute(query)
            event_models = result.scalars().all()
            
            return [Message.from_model(model) for model in event_models] 