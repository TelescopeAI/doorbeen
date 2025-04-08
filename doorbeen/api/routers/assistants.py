import logging
from typing import Annotated, Union, List, Dict, Any, Optional, AsyncGenerator, Generator

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

from doorbeen.api.schemas.requests.assistants import AskLLMRequest
from doorbeen.core.assistants.analysis.sql.query.graph.builder import SQLAgentGraphBuilder
from doorbeen.core.assistants.memory.locations.postgres import PostgresLocation
from doorbeen.core.chat.assistants import AssistantService
from doorbeen.core.config.execution_env import ExecutionEnv
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.connections.clients.service import DBClientService
from doorbeen.core.events.generator import AgentEventGenerator
from doorbeen.core.models.provider import ModelProvider
from doorbeen.core.types.databases import DatabaseTypes
from doorbeen.core.types.outputs import NodeExecutionOutput
from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.users.user import clerk_instance

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


# Create an instance of the service


# Then update the route to use the service
@AssistantsRouter.post("/assistants", tags=["Assistants"])
async def ask(request: AskLLMRequest = Body()):
    # Convert to the old request format
    request_data = AskLLMRequest(**request.model_dump())
    assistant_service = AssistantService()
    
    # Determine if we should stream based on the request
    stream = getattr(request, "stream", True)
    
    # Use the service instance
    result = await assistant_service.process_llm_request(request_data, stream=stream)
    
    if stream:
        return StreamingResponse(
            result,
            media_type="application/x-ndjson"
        )
    else:
        return JSONResponse(content=result)
