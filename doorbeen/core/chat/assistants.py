import logging
from typing import Any, Dict, Union, AsyncGenerator, List, Optional, Generator
import uuid
import json

from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from pydantic import ConfigDict, Field

from doorbeen.api.schemas.requests.assistants import AskLLMRequest
from doorbeen.core.assistants.analysis.sql.query.graph.builder import SQLAgentGraphBuilder
from doorbeen.core.assistants.memory.locations.postgres import PostgresLocation
from doorbeen.core.config.execution_env import ExecutionEnv
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.connections.clients.service import DBClientService
from doorbeen.core.events.generator import AgentEventGenerator
from doorbeen.core.models.provider import ModelProvider
from doorbeen.core.types.databases import DatabaseTypes
from doorbeen.core.types.outputs import NodeExecutionOutput
from doorbeen.core.types.ts_model import TSModel


class AssistantService(TSModel):
    memory_location: str = Field(default_factory=lambda: ExecutionEnv.get_key('ASSISTANT_MEMORY_LOCATION_URI'))
    """Service class to handle LLM assistant operations."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

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

    async def build_agent_graph(self, model_handler: Any, question: str, checkpointer: AsyncPostgresSaver) -> Any:
        """Build and return the agent graph for processing the question."""
        graph_builder = SQLAgentGraphBuilder(handler=model_handler, question=question)
        graph = graph_builder.build(checkpointer)

        # Generate and save graph visualization using Mermaid.Ink
        try:
            logging.info("[GRAPH_VIZ] Generating graph visualization...")
            
            # Get the graph PNG using Mermaid.Ink API (default method)
            graph_png_data = graph.get_graph().draw_mermaid_png()
            
            # Save the image with the specified name
            with open("workflow.png", "wb") as f:
                f.write(graph_png_data)
            
            # Log the size of the generated image
            logging.info(f"[GRAPH_VIZ] Generated graph image: {len(graph_png_data)} bytes")
            logging.info(f"[GRAPH_VIZ] Saved graph visualization as 'workflow-dag.png'")
            
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

    def create_graph_config(self, connection: Any, thread_id: str = None) -> Dict[str, Any]:
        """Create and return the configuration for the graph."""
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        return {
            "configurable": {
                # fetch the user's database connection
                "connection": connection,
                # Checkpoints are accessed by thread_id
                "thread_id": thread_id,
            },
            # Increase recursion limit to handle complex analysis workflows
            "recursion_limit": 50
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
                        yield error_event.model_dump_json() + "\n"
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
                        yield termination_event.model_dump_json() + "\n"
                        
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

    def process_event_chunk(self, event: Dict[str, Any], collect: bool = False) -> Generator[str | Any, Any, None]:
        """Process a single event chunk and yield/return the result."""
        for key, value in event.items():
            print(f"\n=== NODE: {key} ===")
            logging.info(f"=== NODE: {key} ===")
            
            if isinstance(value["messages"][-1], AIMessage):
                content = value["messages"][-1].content
                execution_output = NodeExecutionOutput(name=key, value=content)
                event_obj = AgentEventGenerator(chunk=execution_output).process_chunk()
                
                # Pretty print the data for console readability
                try:
                    parsed_data = json.loads(event_obj.data)
                    formatted_data = json.dumps(parsed_data, indent=2, default=str)
                    print(f"Data:\n{formatted_data}")
                    logging.info(f"Data:\n{formatted_data}")
                except (json.JSONDecodeError, TypeError):
                    # Fallback to original if not valid JSON
                    print(f"Data: {event_obj.data}")
                    logging.info(f"Data: {event_obj.data}")
                
                print(f"Occurred at: {event_obj.occurred_at}")
                print("=" * 50)
                logging.info(f"Occurred at: {event_obj.occurred_at}")

                if collect:
                    yield event_obj.model_dump()
                else:
                    # Yield JSON string with a newline
                    yield event_obj.model_dump_json() + "\n"

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
        graph = await self.build_agent_graph(model_handler, request.question, checkpointer)
        config = self.create_graph_config(connection)

        # Process and return results - pass the connection
        return await self.process_graph_events(graph, request.question, config, conn, stream)