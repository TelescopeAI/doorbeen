import logging
from typing import Annotated, Union, List, Dict, Any, Optional, AsyncGenerator

import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import RequestState, AuthenticateRequestOptions
from fastapi import APIRouter, Body
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from starlette.responses import StreamingResponse, JSONResponse

from api.schemas.requests.assistants import AskLLMRequest, AskLLMRequestV2
from core.assistants.analysis.sql.query.graph.builder import SQLAgentGraphBuilder
from core.assistants.memory.locations.postgres import PostgresLocation
from core.config.execution_env import ExecutionEnv
from core.connections.clients.SQL.common import CommonSQLClient
from core.connections.clients.service import DBClientService
from core.events.generator import AgentEventGenerator
from core.models.provider import ModelProvider
from core.types.databases import DatabaseTypes
from core.types.outputs import NodeExecutionOutput
from core.users.user import clerk_instance

AssistantsRouter = APIRouter()
memory = MemorySaver()


async def sdk() -> Clerk:
    sdk = clerk_instance
    return sdk


async def request_state(
        request: Request,
        _: Annotated[HTTPAuthorizationCredentials, Security(HTTPBearer())],
        sdk: Clerk = Security(sdk),
) -> RequestState:
    # Convert FastAPI request headers to httpx format
    httpx_request = httpx.Request(
        method=request.method, url=str(request.url), headers=dict(request.headers)
    )
    # Fetch comma-separated domains and convert them to a list
    allowed_parties = [party.strip() for party in ExecutionEnv.get_key('CLERK_ALLOWED_PARTIES').split(',')]

    auth_options = AuthenticateRequestOptions(
        secret_key=ExecutionEnv.get_key('CLERK_BACKEND_API_KEY'),
        authorized_parties=allowed_parties,
    )
    # Authenticate request
    auth_state: RequestState = sdk.authenticate_request(
        httpx_request,
        auth_options
    )

    return auth_state


async def authed_request_state(
        request: Request,
        request_state: RequestState = Security(request_state),
) -> RequestState:
    print(f"Request State: {request_state}")
    if not request_state.is_signed_in:
        raise HTTPException(status_code=401, detail=request_state.message)

    return request_state


async def setup_database_connection(request: AskLLMRequest) -> Optional[Any]:
    """Set up database connection based on request credentials."""
    db_type = request.connection.db_type
    is_common_sql = db_type in [DatabaseTypes.POSTGRESQL, DatabaseTypes.MYSQL, DatabaseTypes.ORACLE,
                              DatabaseTypes.SQLITE]
    
    if not is_common_sql:
        logging.info(f"Database type {db_type} is not a common SQL type")
        return None
        
    client: CommonSQLClient = DBClientService.get_client(
        details=request.connection.credentials,
        db_type=request.connection.db_type
    )
    connection = client.connect()
    logging.info(f"Connected to {db_type} database")
    return connection


async def setup_model_handler(request: AskLLMRequest) -> Any:
    """Initialize and return the appropriate model handler."""
    logging.info("[LOG] Setting up model handler")
    manufacturer = "OpenAI" if request.model.name.startswith("gpt-") else None
    model_handler = ModelProvider().get_model_instance(
        model_name=request.model.name, 
        api_key=request.model.api_key
    )
    return model_handler


async def setup_memory_checkpointer() -> AsyncPostgresSaver:
    """Set up and return the memory checkpointer."""
    loc_uri = ExecutionEnv.get_key('ASSISTANT_MEMORY_LOCATION_URI')
    mem_loc = PostgresLocation(db_uri=loc_uri)
    logging.info(f"DB Mem Loc: {mem_loc.db_uri}")
    
    conn = await AsyncConnection.connect(mem_loc.db_uri, **mem_loc.config.model_dump())
    checkpointer = AsyncPostgresSaver(conn)
    await checkpointer.setup()
    return checkpointer, conn


async def build_agent_graph(model_handler: Any, question: str, checkpointer: AsyncPostgresSaver) -> Any:
    """Build and return the agent graph for processing the question."""
    graph_builder = SQLAgentGraphBuilder(handler=model_handler, question=question)
    graph = graph_builder.build(checkpointer)
    
    # Save graph visualization for debugging
    graph_details = graph.get_graph().draw_mermaid_png()
    with open("workflow.png", "wb") as f:
        f.write(graph_details)
        
    return graph


def create_graph_config(connection: Any, thread_id: str = "5") -> Dict[str, Any]:
    """Create and return the configuration for the graph."""
    return {
        "configurable": {
            # fetch the user's database connection
            "connection": connection,
            # Checkpoints are accessed by thread_id
            "thread_id": thread_id,
        }
    }


async def process_graph_events(
    graph: Any, 
    question: str, 
    config: Dict[str, Any],
    conn: AsyncConnection,  # Pass the connection
    stream: bool = True
) -> Union[AsyncGenerator[str, None], List[Dict]]:
    """
    Process graph events and return either a streaming generator or collected responses.
    """
    try:
        if stream:
            async def generate_response():
                try:
                    async for event in graph.astream({"messages": ("user", question)}, config=config):
                        for chunk in process_event_chunk(event):
                            yield chunk
                finally:
                    # Ensure connection is closed when streaming is done
                    await conn.close()
            return generate_response()
        else:
            responses = []
            async for event in graph.astream({"messages": ("user", question)}, config=config):
                for chunk in process_event_chunk(event, collect=True):
                    responses.append(chunk)
            return responses
    finally:
        # Only close here for non-streaming case
        if not stream:
            await conn.close()


def process_event_chunk(event: Dict[str, Any], collect: bool = False) -> Union[str, Dict]:
    """Process a single event chunk and yield/return the result."""
    for key, value in event.items():
        print("Key:", key)
        logging.info(f"Key: {key}")
        logging.info(f"Value: {value}")
        if isinstance(value["messages"][-1], AIMessage):
            content = value["messages"][-1].content
            execution_output = NodeExecutionOutput(name=key, value=content)
            event_obj = AgentEventGenerator(chunk=execution_output).process_chunk()
            print("Assistant:", event_obj)
            logging.info(f"Assistant: {event_obj.model_dump_json(indent=4)}")
            
            if collect:
                yield event_obj.model_dump()
            else:
                # Yield JSON string with a newline
                yield event_obj.model_dump_json() + "\n"


async def process_llm_request(request: AskLLMRequest, stream: bool = True):
    """Process an LLM request and return the response."""
    logging.info("[LOG] New Request Starts here")
    print("New Request Starts here")
    
    # Set up components
    connection = await setup_database_connection(request)
    model_handler = await setup_model_handler(request)
    
    # Set up memory and checkpointer
    checkpointer, conn = await setup_memory_checkpointer()
    
    # Build graph and configure
    graph = await build_agent_graph(model_handler, request.question, checkpointer)
    config = create_graph_config(connection)
    
    # Process and return results - pass the connection
    return await process_graph_events(graph, request.question, config, conn, stream)


@AssistantsRouter.post("/assistants", tags=["Assistants"])
async def ask(request: AskLLMRequestV2 = Body()):
    # Convert to the old request format
    request_data = AskLLMRequest(**request.model_dump())
    
    # Determine if we should stream based on the request
    stream = getattr(request, "stream", True)
    
    result = await process_llm_request(request_data, stream=stream)
    
    if stream:
        return StreamingResponse(
            result,
            media_type="application/x-ndjson"
        )
    else:
        return JSONResponse(content=result)
