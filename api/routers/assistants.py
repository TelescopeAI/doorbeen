import logging
from typing import Annotated

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
from starlette.responses import StreamingResponse

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


@AssistantsRouter.post("/assistants", tags=["Assistants"])
async def ask(request: AskLLMRequestV2 = Body()):
    request = AskLLMRequest(**request.model_dump())
    db_type = request.connection.db_type
    is_common_sql = db_type in [DatabaseTypes.POSTGRESQL, DatabaseTypes.MYSQL, DatabaseTypes.ORACLE,
                                DatabaseTypes.SQLITE]
    connection = None
    if is_common_sql:
        client: CommonSQLClient = DBClientService.get_client(details=request.connection.credentials,
                                                             db_type=request.connection.db_type)
        connection = client.connect()

    # graph_builder = StateGraph(SQLAssistantState)
    #
    logging.info("[LOG] New Request Starts here")
    print("New Request Starts here")
    manufacturer = "OpenAI" if request.model.name.startswith("gpt-") else None
    model_handler = ModelProvider().get_model_instance(model_name=request.model.name, api_key=request.model.api_key)

    # Clerk Instance
    clerk = clerk_instance

    async def generate_response():
        loc_uri = ExecutionEnv.get_key('ASSISTANT_MEMORY_LOCATION_URI')
        mem_loc = PostgresLocation(db_uri=loc_uri)
        checkpointer = None
        print(f"DB Mem Loc: {mem_loc.db_uri}")
        async with await AsyncConnection.connect(mem_loc.db_uri, **mem_loc.config.model_dump()) as conn:
            checkpointer = AsyncPostgresSaver(conn)
            # NOTE: you need to call .setup() the first time you're using your checkpointer
            await checkpointer.setup()
            graph_builder = SQLAgentGraphBuilder(handler=model_handler, question=request.question)
            graph = graph_builder.build(checkpointer)
            graph_details = graph.get_graph().draw_mermaid_png()

            # display(Image(graph_details))
            # Save image to file
            with open("workflow.png", "wb") as f:
                f.write(graph_details)
            thread_id = "5"

            config = {
                "configurable": {
                    # fetch the user's database connection
                    "connection": connection,
                    # Checkpoints are accessed by thread_id
                    "thread_id": thread_id,
                }
            }

            async for event in graph.astream({"messages": ("user", request.question)}, config=config):
                for key, value in event.items():
                    print("Key:", key)
                    logging.info(f"Key: {key}")
                    logging.info(f"Value: {value}")
                    if isinstance(value["messages"][-1], AIMessage):
                        content = value["messages"][-1].content
                        execution_output = NodeExecutionOutput(name=key, value=content)
                        event = AgentEventGenerator(chunk=execution_output).process_chunk()
                        print("Assistant:", event)
                        logging.info(f"Assistant: {event.model_dump_json(indent=4)}")
                        # Yield JSON string with a newline
                        yield event.model_dump_json() + "\n"

    return StreamingResponse(
        generate_response(),
        media_type="application/x-ndjson"
    )
