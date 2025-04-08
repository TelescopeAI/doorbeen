from typing import Union

from deprecated import deprecated
from fastapi import APIRouter, Body, WebSocket
from starlette.responses import StreamingResponse

from doorbeen.api.schemas.requests.assistants import AskLLMRequest
from doorbeen.api.utils.sockets.common import WebSocketManager
from doorbeen.core.agents.sql import SQLAgent
from doorbeen.core.connections.clients.SQL.bigquery import BigQueryClient
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.connections.clients.service import DBClientService
from doorbeen.core.events.generator import AgentEventGenerator
from doorbeen.core.models.model import ModelInstance
from doorbeen.core.types.databases import DatabaseTypes

SQLAgentRouter = APIRouter()

# Deprecation message
DEPRECATION_MESSAGE = ("The Agents API is deprecated because we moved to a better system which is the Assistants API. "
                       "Use that instead.")


@deprecated(reason=DEPRECATION_MESSAGE)
def text_to_md(text: str):
    return text


@deprecated(reason=DEPRECATION_MESSAGE)
def ask_db_agent(request: Union[dict, AskLLMRequest]):
    if isinstance(request, dict):
        request = AskLLMRequest(**request)
    db_type = request.connection.db_type
    is_common_sql = db_type in [DatabaseTypes.POSTGRESQL, DatabaseTypes.MYSQL, DatabaseTypes.ORACLE,
                                DatabaseTypes.SQLITE]
    if is_common_sql:
        client: CommonSQLClient = DBClientService.get_client(details=request.connection.credentials,
                                                             db_type=request.connection.db_type)

    connection = client.connect()
    sql_agent = SQLAgent(client=client, db_type=db_type)
    manufacturer = "OpenAI" if request.model.name.startswith("gpt-") else None
    model = ModelInstance(name=request.model.name, api_key=request.model.api_key, provider=manufacturer)
    if request.stream:
        return sql_agent.ask_langchain_agent(model=model, question=request.question, engine=connection.engine,
                                             stream=True)
    else:
        return sql_agent.ask_langchain_agent(model=model, question=request.question, engine=connection.engine)


@SQLAgentRouter.post("/sql/agents", tags=["Agents"])
@deprecated(reason=DEPRECATION_MESSAGE)
async def ask(request: AskLLMRequest = Body()):
    request = AskLLMRequest(**request.model_dump())
    connection = None
    client = None
    db_type = request.connection.db_type
    if db_type == DatabaseTypes.BIGQUERY:
        client: BigQueryClient = DBClientService.get_client(details=request.connection.credentials,
                                                            db_type=request.connection.db_type)
    engine = client.get_engine()

    connection = client.connect()
    sql_agent = SQLAgent(client=client, db_type=db_type)
    return sql_agent.ask_langchain_agent(question=request.question, stream=True, engine=engine)


@SQLAgentRouter.post("/sql/agents/new", tags=["Agents"])
@deprecated(reason=DEPRECATION_MESSAGE)
async def ask_new(request: AskLLMRequest = Body()):
    request = AskLLMRequest(**request.model_dump())

    async def response_generator():
        async for chunk in ask_db_agent(request):
            event = AgentEventGenerator(chunk=chunk).process_chunk()
            yield event

    if request.stream:
        return StreamingResponse(
            response_generator(),
            media_type="text/event-stream"
        )
    else:
        agent_response = []
        async for chunk in ask_db_agent(request):
            agent_response.append(chunk)
        return agent_response[0] if agent_response else None


@SQLAgentRouter.websocket("/agents")
@deprecated(reason=DEPRECATION_MESSAGE)
async def ws_ask_new(websocket: WebSocket):
    async def message_handler(request_data):
        async for chunk in ask_db_agent(request_data):
            yield chunk.model_dump()

    ws_manager = WebSocketManager(websocket=websocket)
    await ws_manager.run(message_handler)


@SQLAgentRouter.websocket("/explain")
@deprecated(reason=DEPRECATION_MESSAGE)
async def explain(websocket: WebSocket):
    async def message_handler(request_data):
        request = AskLLMRequest(**request_data)
        db_type = request.connection.db_type
        is_common_sql = db_type in [DatabaseTypes.POSTGRESQL, DatabaseTypes.MYSQL, DatabaseTypes.ORACLE,
                                    DatabaseTypes.SQLITE]
        if is_common_sql:
            client: CommonSQLClient = DBClientService.get_client(details=request.connection.credentials,
                                                                 db_type=request.connection.db_type)

        connection = client.connect()
        sql_agent = SQLAgent(client=client, db_type=db_type)
        manufacturer = "OpenAI" if request.model.name.startswith("gpt-") else None
        model = ModelInstance(name=request.model.name, api_key=request.model.api_key, provider=manufacturer)

        async for chunk in sql_agent.ask_langchain_agent(model=model, question=request.question,
                                                         engine=connection.engine, stream=True):
            yield chunk

    ws_manager = WebSocketManager(websocket=websocket)
    await ws_manager.run(message_handler)
