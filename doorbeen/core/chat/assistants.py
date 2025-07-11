import logging
from typing import Any, Dict, Union, AsyncGenerator, List, Optional, Generator
import uuid
import json
from datetime import datetime
from uuid import UUID
import aiohttp
import traceback

from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from pydantic import ConfigDict, Field
from pydantic.json import pydantic_encoder

# Import storage system components
from doorbeen.core.storage import StorageManager, StorageConfig, CheckpointerFactory

from doorbeen.api.schemas.requests.assistants import AskLLMRequest
from doorbeen.core.assistants.analysis.sql.query.graph.builder import SQLGraphBuilder
from doorbeen.core.assistants.memory.locations.postgres import PostgresLocation
from doorbeen.core.config.execution_env import ExecutionEnv
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.connections.clients.service import DBClientService
from doorbeen.core.events.generator import AgentEventGenerator
from doorbeen.core.events.processor import LangGraphEventProcessor
from doorbeen.core.models.provider import ModelProvider
from doorbeen.core.types.databases import DatabaseTypes
from doorbeen.core.types.outputs import NodeExecutionOutput
from doorbeen.core.types.ts_model import TSModel

from doorbeen.api.schemas.requests.assistants import AskLLMRequest
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.grounding.loader import prepare_examples_for_state


class AssistantService(TSModel):
    memory_location: str = Field(default_factory=lambda: ExecutionEnv.get_key('ASSISTANT_MEMORY_LOCATION_URI'))
    """Service class to handle LLM assistant operations."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Storage system components
    storage_config: Optional[StorageConfig] = Field(default=None)
    storage_manager: Optional[StorageManager] = Field(default=None)

    async def setup_database_connection(self, request: AskLLMRequest) -> Optional[Any]:
        """Set up database connection based on request credentials."""
        logging.info(f"[DB_CONNECTION] Setting up database connection")
        logging.info(f"[DB_CONNECTION] Request connection data: {request.connection}")
        logging.info(f"[DB_CONNECTION] DB type: {request.connection.db_type}")
        logging.info(f"[DB_CONNECTION] Credentials: {request.connection.credentials}")
        
        db_type = request.connection.db_type
        is_common_sql = db_type in [DatabaseTypes.POSTGRESQL, DatabaseTypes.MYSQL, DatabaseTypes.ORACLE,
                                    DatabaseTypes.SQLITE]

        if not is_common_sql:
            logging.info(f"Database type {db_type} is not a common SQL type")
            return None

        try:
            logging.info(f"[DB_CONNECTION] Creating database client for {db_type}")
            client: CommonSQLClient = DBClientService.get_client(
                details=request.connection.credentials,
                db_type=request.connection.db_type
            )
            logging.info(f"[DB_CONNECTION] Client created successfully")
            logging.info(f"[DB_CONNECTION] Client credentials: {client.credentials}")
            
            # Log the connection URI (but mask the password for security)
            conn_uri = client.get_uri()
            # Mask password in logs
            masked_uri = conn_uri
            if client.credentials.password:
                masked_uri = conn_uri.replace(client.credentials.password, "***MASKED***")
            logging.info(f"[DB_CONNECTION] Connection URI: {masked_uri}")
            
            logging.info(f"[DB_CONNECTION] Attempting to connect...")
            connection = client.connect()
            logging.info(f"Connected to {db_type} database successfully")
            return connection
        except Exception as e:
            logging.error(f"[DB_CONNECTION] Error during database connection setup: {str(e)}")
            logging.error(f"[DB_CONNECTION] Error type: {type(e).__name__}")
            raise

    async def setup_model_handler(self, request: AskLLMRequest) -> Any:
        """Initialize and return the appropriate model handler."""
        logging.info("[LOG] Setting up model handler")
        manufacturer = "OpenAI" if request.model.name.startswith("gpt-") else None
        model_handler = ModelProvider().get_model_instance(
            model_name=request.model.name,
            api_key=request.model.api_key
        )
        return model_handler

    async def setup_memory_checkpointer(self) -> AsyncPostgresSaver:
        """Set up and return the memory checkpointer."""
        loc_uri = self.memory_location
        mem_loc = PostgresLocation(db_uri=loc_uri)
        logging.info(f"DB Mem Loc: {mem_loc.db_uri}")

        conn = await AsyncConnection.connect(mem_loc.db_uri, **mem_loc.config.model_dump())
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()
        return checkpointer, conn

    async def setup_checkpointer(self, config: Optional[StorageConfig] = None) -> tuple[Any, Optional[Any]]:
        """Set up and return a configurable checkpointer using CheckpointerFactory."""
        if config is None:
            config = StorageConfig()
        
        logging.info(f"[STORAGE] Setting up checkpointer type: {config.checkpointer_type}")
        checkpointer, connection = await CheckpointerFactory.create_checkpointer(config)
        logging.info(f"[STORAGE] Checkpointer created: {type(checkpointer).__name__}")
        
        return checkpointer, connection

    async def build_agent_graph(
        self, 
        model_handler: Any, 
        question: str, 
        checkpointer: AsyncPostgresSaver, 
        use_supervisor: bool = False,
        agent_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Build and return the agent graph for processing the question."""
        logging.info(f"[GRAPH_BUILDER] Building agent graph - supervisor mode: {use_supervisor}")
        
        # Create graph builder with supervisor mode configuration
        graph_builder = SQLGraphBuilder(
            handler=model_handler, 
            question=question, 
            use_supervisor=use_supervisor
        )
        
        # Apply agent configuration if provided
        if agent_config:
            logging.info(f"[GRAPH_BUILDER] Applying agent configuration: {agent_config}")
            
            # Note: Agent configuration would be applied here in a production implementation
            # For now, we log it for awareness
        
        # Build the graph using the supervisor feature flag
        mode = "supervisor" if use_supervisor else "linear"
        graph = graph_builder.build(mode=mode, checkpointer=checkpointer)

        # Generate and save graph visualization using Mermaid.Ink
        try:
            logging.info("[GRAPH_VIZ] Generating graph visualization...")
            
            # Get the graph PNG using Mermaid.Ink API (default method)
            graph_png_data = graph.get_graph().draw_mermaid_png()
            
            # Save the image with the specified name
            graph_filename = f"workflow-{'supervisor' if use_supervisor else 'linear'}.png"
            with open(graph_filename, "wb") as f:
                f.write(graph_png_data)
            
            # Log the size of the generated image
            logging.info(f"[GRAPH_VIZ] Generated graph image: {len(graph_png_data)} bytes")
            logging.info(f"[GRAPH_VIZ] Saved graph visualization as '{graph_filename}'")
            
            # Optionally, you can also get the Mermaid syntax for logging
            mermaid_syntax = graph.get_graph().draw_mermaid()
            logging.info(f"[GRAPH_VIZ] Mermaid syntax generated: {len(mermaid_syntax)} characters")
            
            # Print first few lines of Mermaid syntax for debugging
            mermaid_lines = mermaid_syntax.split('\n')[:10]
            logging.info(f"[GRAPH_VIZ] Mermaid preview: {' | '.join(mermaid_lines)}")
            
        except Exception as e:
            logging.error(f"[GRAPH_VIZ] Failed to generate graph visualization: {str(e)}")
            logging.error(f"[GRAPH_VIZ] Error type: {type(e).__name__}")

        return graph

    def create_graph_config(self, connection: Any, handler: Any, thread_id: str = None, examples: list = None) -> Dict[str, Any]:
        """Create and return the configuration for the graph."""
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        
        # Prepare examples for state
        prepared_examples = prepare_examples_for_state(examples)
        
        return {
            "configurable": {
                # fetch the user's database connection
                "connection": connection,
                # Pass model handler to nodes
                "handler": handler,
                # Checkpoints are accessed by thread_id
                "thread_id": thread_id,
                # Pass storage_manager to nodes for thread message access
                "storage_manager": self.storage_manager,
                # Initial state with examples
                "initial_state": {
                    "past_examples": prepared_examples
                }
            },
            # Increase recursion limit to handle complex analysis workflows
            "recursion_limit": 100
        }

    async def process_graph_events(
            self,
            graph: Any,
            question: str,
            config: Dict[str, Any],
            conn: AsyncConnection,
            stream: bool = True
    ) -> Union[AsyncGenerator[str, None], List[Dict]]:
        """
        Process graph events and return either a streaming generator or collected responses.
        """
        try:
            if stream:
                async def generate_response():
                    event_count = 0
                    circuit_breaker_triggered = False
                    last_node_processed = None
                    
                    try:
                        async for event in graph.astream({"messages": ("user", question)}, config=config):
                            event_count += 1
                            
                            # Check for circuit breaker in the event
                            for key, value in event.items():
                                last_node_processed = key
                                if isinstance(value.get("messages", [{}])[-1], AIMessage):
                                    content = value["messages"][-1].content
                                    try:
                                        if isinstance(content, str):
                                            parsed_content = json.loads(content)
                                            if parsed_content.get("circuit_breaker_triggered"):
                                                circuit_breaker_triggered = True
                                    except (json.JSONDecodeError, TypeError):
                                        pass
                            
                            for chunk in self.process_event_chunk(event):
                                yield chunk
                                
                    except Exception as e:
                        # Send error termination message
                        error_output = NodeExecutionOutput(name="system_error", value=f"Stream terminated due to error: {str(e)}")
                        error_event = AgentEventGenerator(chunk=error_output).process_chunk()
                        yield error_event.model_dump()
                        circuit_breaker_triggered = True
                        
                    finally:
                        # Determine appropriate termination reason
                        if circuit_breaker_triggered:
                            termination_reason = "circuit_breaker_triggered"
                        elif event_count == 0:
                            termination_reason = "no_events_processed"
                        else:
                            termination_reason = "graph_completed"
                        
                        # Send final termination message to notify frontend that streaming is complete
                        termination_data = {
                            "streaming_complete": True,
                            "total_events_processed": event_count,
                            "termination_reason": termination_reason,
                            "circuit_breaker_triggered": circuit_breaker_triggered,
                            "last_node_processed": last_node_processed
                        }
                        
                        # Create a special termination node output
                        termination_output = NodeExecutionOutput(
                            name="stream_termination", 
                            value=json.dumps(termination_data)
                        )
                        termination_event = AgentEventGenerator(chunk=termination_output).process_chunk()
                        yield termination_event.model_dump()
                        
                        # Ensure connection is closed when streaming is done
                        await conn.close()

                return generate_response()
            else:
                responses = []
                async for event in graph.astream({"messages": ("user", question)}, config=config):
                    for chunk in self.process_event_chunk(event, collect=True):
                        responses.append(chunk)
                return responses
        finally:
            # Only close here for non-streaming case
            if not stream:
                await conn.close()

    def process_event_chunk(self, event: Union[Dict[str, Any], tuple], collect: bool = False) -> Generator[Union[str, Any], Any, None]:
        """Process a single event chunk and yield/return the result."""
        if isinstance(event, tuple):
            # Handle token stream from stream_mode="messages"
            token_chunk, metadata = event
            if not getattr(token_chunk, 'content', None):
                return
            
            event_output = NodeExecutionOutput(
                name=metadata.get("node", "llm"),
                value=token_chunk.content
            )
            event_obj = AgentEventGenerator(chunk=event_output, event_type="token").process_chunk()

            if collect:
                yield event_obj.model_dump()
            else:
                yield event_obj.model_dump()

        elif isinstance(event, dict):
            # This is a chunk from stream_mode="updates"
            for key, value in event.items():
                print(f"\n=== NODE: {key} ===")
                logging.info(f"=== NODE: {key} ===")
            
                if value.get("messages") and isinstance(value["messages"][-1], AIMessage):
                    content = value["messages"][-1].content
                    
                    # Ensure the content is always a structured object
                    try:
                        # If content is a JSON string, parse it.
                        parsed_content = json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        # If not, wrap it in a standard text object.
                        parsed_content = {"type": "text", "content": content}

                    execution_output = NodeExecutionOutput(name=key, value=parsed_content)
                    event_obj = AgentEventGenerator(chunk=execution_output).process_chunk()
                    execution_output.model_dump_json()
                
                # Pretty print the data for console readability
                try:
                    formatted_data = json.dumps(parsed_content, indent=2, default=str)
                    print(f"Data:\n{formatted_data}")
                    logging.info(f"Data:\n{formatted_data}")
                except (json.JSONDecodeError, TypeError):
                    # Fallback to original if not valid JSON
                        # This should ideally not happen anymore with the above logic
                    print(f"Data: {event_obj.data}")
                    logging.info(f"Data: {event_obj.data}")
                
                print(f"Occurred at: {event_obj.occurred_at}")
                print("=" * 50)
                logging.info(f"Occurred at: {event_obj.occurred_at}")

                if collect:
                    yield event_obj.model_dump()
                else:
                    # Yield JSON string with a newline
                        yield event_obj.model_dump_json()

    async def process_llm_request(self, request: AskLLMRequest, stream: bool = True):
        """Process an LLM request and return the response."""
        logging.info("[LOG] New Request Starts here")
        print("New Request Starts here")

        # Set up components
        connection = await self.setup_database_connection(request)
        model_handler = await self.setup_model_handler(request)

        # Set up memory and checkpointer
        checkpointer, conn = await self.setup_memory_checkpointer()

        # Build graph and configure
        graph = await self.build_agent_graph(
            model_handler, 
            request.question, 
            checkpointer,
            use_supervisor=getattr(request, 'use_supervisor', False),
            agent_config=getattr(request, 'agent_config', None)
        )
        config = self.create_graph_config(connection, model_handler)

        # Process and return results - pass the connection
        return await self.process_graph_events(graph, request.question, config, conn, stream)

    async def process_llm_request_with_storage(
        self, 
        request: AskLLMRequest, 
        thread_id: Optional[UUID] = None, 
        stream: bool = True
    ):
        """
        Process an LLM request with storage capabilities.
        
        This method provides unified streaming with thread-based conversation storage.
        It maintains backward compatibility while adding storage features.
        
        Args:
            request: The LLM request
            thread_id: Optional thread ID for conversation continuity 
            stream: Whether to stream the response
            
        Returns:
            AsyncGenerator for streaming or List for non-streaming responses
        """
        logging.info("[STORAGE] New request with storage support")
        
        # 1. Initialize storage manager if not already done
        if self.storage_manager is None:
            self.storage_config = StorageConfig()
            self.storage_manager = StorageManager(self.storage_config)
            await self.storage_manager.initialize()
            logging.info("[STORAGE] Storage manager initialized")
        
        # 2. Handle thread creation/retrieval
        if thread_id is None and request.thread_id is not None:
            thread_id = request.thread_id
            
        if thread_id is None:
            # Create new thread
            thread_metadata = {
                "model": request.model.name,
                "db_type": request.connection.db_type.value,
                "created_from": "assistant_request"
            }
            thread = await self.storage_manager.create_thread(thread_metadata)
            thread_id = thread.id
            logging.info(f"[STORAGE] Created new thread: {thread_id}")
        else:
            # Verify thread exists
            thread = await self.storage_manager.get_thread(thread_id)
            if thread is None:
                raise ValueError(f"Thread {thread_id} not found")
            logging.info(f"[STORAGE] Using existing thread: {thread_id}")
        
        # 3. Store user message
        user_message_metadata = request.message_metadata or {}
        user_message_metadata.update({
            "model": request.model.name,
            "db_type": request.connection.db_type.value
        })
        
        user_message = await self.storage_manager.create_message(
            thread_id=thread_id,
            content=request.question,
            role="user",
            metadata=user_message_metadata
        )
        logging.info(f"[STORAGE] Stored user message: {user_message.id}")
        
        # 4. Set up components
        connection = await self.setup_database_connection(request)
        model_handler = await self.setup_model_handler(request)
        
        # 5. Set up pluggable checkpointer
        checkpointer, checkpointer_conn = await self.setup_checkpointer(self.storage_config)
        
        # 6. Build graph and configure with thread_id
        graph = await self.build_agent_graph(
            model_handler, 
            request.question, 
            checkpointer,
            use_supervisor=getattr(request, 'use_supervisor', False),
            agent_config=getattr(request, 'agent_config', None)
        )
        config = self.create_graph_config(
            connection, 
            model_handler, 
            str(thread_id),
            examples=getattr(request, 'examples', None)
        )
        
        # 7. Decide whether to stream or collect results
        if stream:
            logging.info("[STREAMING] Processing LLM request with streaming response")
            return self._unified_streaming_response(
                graph, request, config, checkpointer_conn, 
                thread_id, user_message.id, stream
            )
        else:
            responses = []
            async for event in graph.astream({"messages": ("user", request.question)}, config=config):
                for chunk in self.process_event_chunk(event, collect=True):
                    responses.append(chunk)
            
            # Store assistant response for non-streaming
            if responses:
                assistant_content = self._extract_final_response(responses)
                await self.storage_manager.create_message(
                    thread_id=thread_id,
                    content=assistant_content,
                    role="assistant", 
                    metadata={"model": request.model.name}
                )
            
            # Clean up resources
            await CheckpointerFactory.cleanup_checkpointer(checkpointer, checkpointer_conn)
            
            return responses

    async def _unified_streaming_response(
        self,
        graph: Any,
        request: AskLLMRequest,
        config: Dict[str, Any],
        checkpointer_conn: Optional[Any],
        thread_id: UUID,
        user_message_id: UUID,
        stream: bool
    ) -> AsyncGenerator[str, None]:
        """
        Unified streaming implementation with storage.
        
        This generator yields:
        1. Thread creation event (if new thread)
        2. Streaming graph execution events (with real-time storage)
        3. Final message storage event
        4. Completion event
        """
        assistant_message_id = None
        stored_events = []
        event_processor = LangGraphEventProcessor()
        
        try:
            # Yield thread information event
            thread_info_data = {
                "thread_id": str(thread_id),
                "user_message_id": str(user_message_id),
            }
            thread_info_output = NodeExecutionOutput(
                name="thread_info", 
                value=thread_info_data
            )
            thread_event = AgentEventGenerator(
                chunk=thread_info_output, 
                event_type="info"
            ).process_chunk()
            yield json.dumps(thread_event, default=pydantic_encoder)
            
            # Create assistant message placeholder early
            assistant_message = await self.storage_manager.create_message(
                thread_id=thread_id,
                content="[Analysis in progress...]",
                role="assistant",
                metadata={
                    "model": config.get("model", "unknown"),
                    "status": "streaming",
                    "user_message_id": str(user_message_id)
                }
            )
            assistant_message_id = assistant_message.id
            logging.info(f"[STORAGE] Created assistant message placeholder: {assistant_message_id}")
            
            # Use astream with "updates" mode to get structured agent progress.
            async for event in graph.astream(
                {"messages": [("user", request.question)]},
                config=config,
                stream_mode="updates",
            ):
                # Transform the raw langgraph event into our custom AgentEvent
                for agent_event in event_processor.transform_event(event):
                    event_json = json.dumps(agent_event, default=pydantic_encoder)
                    
                    # Store the event in the database
                    await self._store_agent_event_if_needed(
                        event_json, thread_id, assistant_message_id, stored_events
                    )
                    
                    # Yield the event to the frontend
                    yield event_json
                    
        except Exception as e:
            # Send error termination message
            error_event = {
                "event": "error",
                "data": { "error": str(e), "error_type": type(e).__name__ }
            }
            yield json.dumps(error_event)
            logging.error(f"[ASSISTANT_SERVICE] Streaming error: {e}\n{traceback.format_exc()}")
            
        finally:
            try:
                # Send stream termination event to notify frontend
                termination_data = {
                    "streaming_complete": True,
                    "thread_id": str(thread_id),
                    "assistant_message_id": str(assistant_message_id) if assistant_message_id else None,
                    "termination_reason": "graph_completed"
                }
                
                # Create a special termination node output
                termination_output = NodeExecutionOutput(
                    name="stream_termination", 
                    value=termination_data
                )
                termination_event = AgentEventGenerator(
                    chunk=termination_output
                ).process_chunk()
                yield json.dumps(termination_event, default=pydantic_encoder)
                
                logging.info(f"[STREAMING] Stream termination event sent for thread: {thread_id}")
                
                # Final message update and cleanup would go here, but let's focus on streaming first.
                # This part can be refactored later to handle the final state from the event stream.
                pass
            finally:
                # Clean up checkpointer resources
                    await CheckpointerFactory.cleanup_checkpointer(None, checkpointer_conn)

    async def _store_agent_event_if_needed(
        self, 
        chunk: str, 
        thread_id: UUID, 
        assistant_message_id: UUID, 
        stored_events: List[str]
    ) -> None:
        """Store agent lifecycle events in real-time as they are generated."""
        try:
            # Parse the chunk to see if it's an agent event
            chunk_data = json.loads(chunk.strip())
            
            # Check if it's an agent event that should be stored
            event_type = chunk_data.get("type", "")
            event_name = chunk_data.get("name", "")
            
            # Define which event types should be stored
            storable_event_types = [
                "agent:start",
                "agent:end", 
                "agent:progress",
                "agent:working",
                "agent:error",
                "agent:warning",
                "agent:handoff",
                "supervisor:routing",
                "assistant:node:output",
                "assistant:llm:output"
            ]
            
            if (event_type in storable_event_types and 
                event_name and 
                chunk_data.get("data")):
                
                # Create a unique identifier for this event to avoid duplicates
                occurred_at = chunk_data.get("occurred_at", "")
                event_signature = f"{event_type}_{event_name}_{occurred_at}"
                
                if event_signature not in stored_events:
                    # Determine the appropriate role based on event type
                    if event_type.startswith("agent:"):
                        role = "agent_lifecycle_event"
                    elif event_type.startswith("supervisor:"):
                        role = "supervisor_event"
                    else:
                        role = "assistant_event"
                    
                    # Extract additional metadata
                    event_data = chunk_data.get("data", {})
                    metadata = {
                        "assistant_message_id": str(assistant_message_id),
                        "event_type": event_type,
                        "event_name": event_name,
                        "occurred_at": occurred_at,
                        "event_signature": event_signature,
                        "category": chunk_data.get("category", ""),
                        "source": chunk_data.get("source", ""),
                        "stage": chunk_data.get("stage", "")
                    }
                    
                    # Add event-specific metadata
                    if isinstance(event_data, dict):
                        if "scope" in event_data:
                            metadata["scope"] = event_data["scope"]
                        if "progress" in event_data:
                            metadata["progress"] = event_data["progress"]
                        if "description" in event_data:
                            metadata["description"] = event_data["description"]
                    
                    # Store the agent event as a separate message
                    await self.storage_manager.create_message(
                        thread_id=thread_id,
                        content=chunk.strip(),  # Store the complete agent event JSON
                        role=role,
                        metadata=metadata
                    )
                    
                    stored_events.append(event_signature)
                    logging.info(f"[STORAGE] Stored {event_type} event: {event_name}")
                    
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Not a parseable agent event, skip storage
            logging.debug(f"[STORAGE] Skipping non-agent event chunk: {str(e)}")
            pass

    def _extract_final_response(self, responses: List[Dict]) -> str:
        """Extract the final response content from collected responses."""
        if not responses:
            return ""
        
        # Get the last response that contains actual content
        for resp in reversed(responses):
            if resp.get("data") and resp["data"] != "null":
                try:
                    data = json.loads(resp["data"]) if isinstance(resp["data"], str) else resp["data"]
                    if isinstance(data, dict) and "value" in data:
                        return str(data["value"])
                    return str(data)
                except (json.JSONDecodeError, TypeError):
                    return str(resp["data"])
        
        return str(responses[-1].get("data", ""))

    async def cleanup_storage(self):
        """Clean up storage resources."""
        if self.storage_manager:
            await self.storage_manager.shutdown()
            self.storage_manager = None
            logging.info("[STORAGE] Storage manager cleaned up")

    async def stream_llm_request_events(self, request: AskLLMRequest):
        """
        Processes an LLM request and streams events using a server-sent events (SSE) format.
        This method is designed to provide real-time, detailed updates on the graph's execution.
        """
        logging.info(f"[ASSISTANT_SERVICE] Starting event stream for request: {request.message}")
        try:
            mode = "supervisor" if getattr(request, 'use_supervisor', False) else "linear"
            logging.info(f"[ASSISTANT_SERVICE] Building graph in '{mode}' mode.")
            graph_builder = SQLGraphBuilder()
            runnable = graph_builder.build(mode=mode)
            
            graph_input = {"messages": [("user", request.message)]}
            config = {"configurable": {"thread_id": request.thread_id}}

            logging.info(f"[ASSISTANT_SERVICE] Starting graph execution stream for thread: {request.thread_id}")
            async for event in runnable.astream_events(graph_input, config, version="v2"):
                yield event

        except Exception as e:
            logging.error(f"[ASSISTANT_SERVICE] Error during event stream processing: {e}")
            logging.error(f"[ASSISTANT_SERVICE] Traceback: {traceback.format_exc()}")
            yield {
                "event": "error",
                "data": {"error": str(e), "error_type": type(e).__name__}
            }
