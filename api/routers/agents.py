import json
import os
import time
from typing import Union

from fastapi import APIRouter, Body, WebSocket
from starlette.responses import StreamingResponse

from api.schemas.requests.agents import AskLLMRequest, DBConnectionRequestParams, AskLLMRequestV2
from api.utils.sockets.common import WebSocketManager
from core.agents.sql import SQLAgent
from core.connections.clients.SQL.bigquery import BigQueryClient
from core.connections.clients.SQL.common import CommonSQLClient
from core.connections.clients.service import DBClientService
from core.events.generator import AgentEventGenerator
from core.models.model import ModelInstance
from core.types.databases import DatabaseTypes
from core.types.manufacturers import ModelProviders

SQLAgentRouter = APIRouter()


def text_to_md(text: str):
    return text


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
async def ask(request: AskLLMRequestV2 = Body()):
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
async def ask_new(request: AskLLMRequestV2 = Body()):
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


# @SQLAgentRouter.post("/agents/execute", tags=["Agents"])
# async def execute_assistant(request: AskLLMRequestV2 = Body()):
#     request = AskLLMRequest(**request.model_dump())
#     connection = None
#     client = None
#     db_type = request.connection.db_type
#     if db_type == DatabaseTypes.MYSQL:
#         client: CommonSQLClient = DBClientService.get_client(details=request.connection.credentials,
#                                                              db_type=request.connection.db_type)
#
#     # Determine the model provider based on the model name
#     if request.model.name.startswith("gpt-"):
#         provider = ModelProviders.OPENAI
#     elif request.model.name.startswith("claude-"):
#         provider = ModelProviders.ANTHROPIC
#     elif request.model.name.startswith("gemini-"):
#         provider = ModelProviders.GOOGLE
#     else:
#         raise ValueError(f"Unknown model provider for model: {request.model.name}")
#
#     connection = client.connect()
#     model = ModelInstance(name=request.model.name, api_key=request.model.api_key, provider=provider)
#     toolkit = TSSQLToolkit(client=client, llm=model)
#     db, toolkit = toolkit.get_lc_tools_from_uri(client.get_uri())
#
#     response = {"tables": [], "schemas": []}
#     response["tables"] = ListSQLDatabaseTool(db=db).run("").split(',')
#     response["query_results"] = QuerySQLDataBaseTool(db=db).run("SELECT * FROM energy_consumption LIMIT 50;")
#     for table in response["tables"]:
#         response["schemas"].append(InfoSQLDatabaseTool(db=db).run(table))
#
#     app = SQLDBWorkflow(db=db).build(model)
#     for event in app.stream(
#             {"messages": [("user", "How many tables are there?")]}
#     ):
#         print(event)
#     return response

    # sql_agent = SQLAssistant(client=client, db_type=db_type, model=model)
    # agent_response = sql_agent.ask_assistant(
    #     question=request.question,
    #     schema=client.credentials.database
    # )
    # Extract usage statistics
    # usage_stats = agent_response.pop("usage_stats")

    # You can now use usage_stats for logging, billing, or any other purpose
    # print(f"Total usage: {usage_stats['total_usage']}")
    # print(f"Usage by model: {usage_stats['usage_by_model']}")

    # return agent_response


@SQLAgentRouter.get("/sandbox/agents/sql", tags=["Agents"])
async def ask(question: str):
    question = question.lower()
    # Check if the question starts with the text "how many accounts do i have"
    if question.startswith("how many accounts do i have"):
        response = {"input": question,
                    "output": "You have a total of 85 accounts \n and the overall portfolio size is 169,543.8"}
        time.sleep(3)
        return response
    elif question.startswith("from this"):
        response = {"input": question,
                    "output": "The accounts based on revenue over 1000 after 2010 are: 1. Groovestreet - Revenue: $30,288 2. Goodsilron - Revenue: $29,617 3. Xx-holding - Revenue: $29,220 4. Cheers - Revenue: $29,166 5. Cheers - Revenue: $27,971 6. Labdrill - Revenue: $27,385 7. Xx-holding - Revenue: $26,186 8. Zoomit - Revenue: $25,897 9. Kan-code - Revenue: $25,791 10. Isdom - Revenue: $4968.91"}
        time.sleep(3)
        return response
    elif question.startswith("now join"):
        response = {"input": question,
                    "output": "Here are the accounts that have revenue over $1000 after the year 2010 and have purchased a product from the GTX line along with the product they've purchased: 1. Account: Isdom, Revenue: $4968.91, Product: GTXPro 2. Account: Labdrill, Revenue: $718.62, Product: GTXPro 3. Account: Xx-holding, Revenue: $497.11, Product: GTXPro"}
        time.sleep(3)
        return response
    else:
        # return {"input": question, "output": "I'm sorry, I don't have an answer for that question."}
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        credentials_file = open(credentials_path, 'r')
        credentials_content = credentials_file.read()
        credentials = json.loads(credentials_content)
        conn_params = {
            'db_type': "bigquery",
            'credentials': {
                'project_id': 'prod-datastore-424523',
                'dataset_id': 'smol_sandbox',
                'service_account_details': credentials
            }
        }
        credentials_file.close()
        connection = DBConnectionRequestParams(**conn_params)
        client = None
        db_type = DatabaseTypes.BIGQUERY
        client: BigQueryClient = DBClientService.get_client(details=connection.credentials,
                                                            db_type=connection.db_type)
        engine = client.get_engine()
        connection = client.connect()
        sql_agent = SQLAgent(client=client, db_type=db_type)
        model_api_key = os.environ.get("OPENAI_API_KEY")
        model = ModelInstance(name="gpt-4o-mini", api_key=model_api_key, manufacturer=ModelProviders.OPENAI)

        answer = sql_agent.ask_langchain_agent(question=question, engine=engine, model=model)
        md_formatted_answer = text_to_md(answer["output"])
        answer["output"] = md_formatted_answer
        return answer


@SQLAgentRouter.websocket("/agents")
async def ws_ask_new(websocket: WebSocket):
    async def message_handler(request_data):
        async for chunk in ask_db_agent(request_data):
            yield chunk.model_dump()

    ws_manager = WebSocketManager(websocket=websocket)
    await ws_manager.run(message_handler)


@SQLAgentRouter.websocket("/explain")
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
