import logging
import traceback
import json
from typing import Annotated

import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import RequestState, AuthenticateRequestOptions
from fastapi import APIRouter, Body
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langgraph.checkpoint.memory import MemorySaver
from starlette.responses import StreamingResponse, JSONResponse

from doorbeen.api.schemas.requests.assistants import AskLLMRequest
from doorbeen.core.chat.assistants import AssistantService
from doorbeen.core.config.execution_env import ExecutionEnv
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
assistant_service = AssistantService()


async def event_streamer(request: AskLLMRequest):
    """
    Generator function that streams events from the assistant service.
    """
    # This unified method will handle both linear and supervisor graphs
    # and will stream events in real-time.
    try:
        # We must 'await' the service method to get the async generator
        async for event in await assistant_service.process_llm_request_with_storage(request, stream=True):
            logging.info(f"[ASSISTANTS_STREAM] Streaming event: {event}")
            # Parse the event to check its type
            try:
                if isinstance(event, str):
                    parsed_event = json.loads(event)
                    if parsed_event.get('type') == 'agent:stream:output':
                        logging.info(f"[ASSISTANTS_STREAM] Specifically streaming agent:stream:output: {parsed_event}")
            except json.JSONDecodeError:
                pass
            yield f"data: {event}\n\n"
    except Exception as e:
        logging.error(f"[ASSISTANTS_STREAM] Error during event streaming: {e}")
        logging.error(f"[ASSISTANTS_STREAM] Traceback: {traceback.format_exc()}")
        error_event = {
            "event": "error",
            "data": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        }
        yield f"data: {json.dumps(error_event, default=str)}\n\n"


# Then update the route to use the service
@AssistantsRouter.post("/assistants", tags=["Assistants"], operation_id="data_analysis")
async def ask(request: AskLLMRequest = Body()):
    try:
        logging.info(f"[ASSISTANTS] Starting new request processing for thread: {request.thread_id}")
        
        # All requests are now treated as streaming via SSE
        return StreamingResponse(
            event_streamer(request),
            media_type="text/event-stream"
        )
            
    except Exception as e:
        logging.error(f"[ASSISTANTS] Unexpected error in ask endpoint: {str(e)}")
        logging.error(f"[ASSISTANTS] Full traceback: {traceback.format_exc()}")
        
        error_message = {
            "error": str(e),
            "error_type": type(e).__name__,
            "status": "error"
        }
        return JSONResponse(
            content=error_message,
            status_code=500
        )
    
