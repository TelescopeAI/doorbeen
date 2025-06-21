import logging
import traceback
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

# Then update the route to use the service
@AssistantsRouter.post("/assistants", tags=["Assistants"], operation_id="data_analysis")
async def ask(request: AskLLMRequest = Body()):
    try:
        logging.info(f"[ASSISTANTS] Starting new request processing")
        logging.info(f"[ASSISTANTS] Request data: {request.model_dump()}")
        
        # Convert to the old request format
        request_data = AskLLMRequest(**request.model_dump())
        logging.info(f"[ASSISTANTS] Creating AssistantService instance")
        assistant_service = AssistantService()
        
        # Determine if we should stream based on the request
        stream = getattr(request, "stream", True)
        logging.info(f"[ASSISTANTS] Stream mode: {stream}")
        
        logging.info(f"[ASSISTANTS] Calling assistant_service.process_llm_request")
        # Use the service instance with timeout handling
        result = await assistant_service.process_llm_request(request_data, stream=stream)
        
        if stream:
            logging.info(f"[ASSISTANTS] Returning StreamingResponse")
            return StreamingResponse(
                result,
                media_type="application/x-ndjson"
            )
        else:
            logging.info(f"[ASSISTANTS] Returning JSONResponse")
            return JSONResponse(content=result)
            
    except httpx.ReadTimeout as e:
        logging.error(f"[ASSISTANTS] Timeout error: {str(e)}")
        logging.error(f"[ASSISTANTS] Timeout traceback: {traceback.format_exc()}")
        error_message = {
            "error": "Request timed out. The operation took longer than expected to complete.",
            "status": "timeout"
        }
        return JSONResponse(
            content=error_message,
            status_code=504  # Gateway Timeout
        )
    except Exception as e:
        logging.error(f"[ASSISTANTS] Unexpected error: {str(e)}")
        logging.error(f"[ASSISTANTS] Error type: {type(e).__name__}")
        logging.error(f"[ASSISTANTS] Full traceback: {traceback.format_exc()}")
        
        # Also log to stdout for immediate visibility
        print(f"[ASSISTANTS] Unexpected error: {str(e)}")
        print(f"[ASSISTANTS] Error type: {type(e).__name__}")
        print(f"[ASSISTANTS] Full traceback: {traceback.format_exc()}")
        
        error_message = {
            "error": str(e),
            "error_type": type(e).__name__,
            "status": "error"
        }
        return JSONResponse(
            content=error_message,
            status_code=500
        )
    
