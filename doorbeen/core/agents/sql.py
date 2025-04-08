from typing import Any, Union

from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_core.outputs import LLMResult

from doorbeen.core.connections.clients.NoSQL.mongo import MongoDBClient
from doorbeen.core.connections.clients.SQL.bigquery import BigQueryClient
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.model import ModelInstance
from doorbeen.core.types.databases import DatabaseTypes
from doorbeen.core.types.ts_model import TSModel


class AsyncCallbackHandler(AsyncIteratorCallbackHandler):
    content: str = ""
    final_answer: bool = False

    def __init__(self) -> None:
        super().__init__()

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.content += token
        # if we passed the final answer, we put tokens in queue
        if self.final_answer:
            if '"action_input": "' in self.content:
                if token not in ['"', "}"]:
                    self.queue.put_nowait(token)
        elif "Final Answer" in self.content:
            self.final_answer = True
            self.content = ""

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        if self.final_answer:
            self.content = ""
            self.final_answer = False
            self.done.set()
        else:
            self.content = ""


class SQLAgent(TSModel):
    client: Union[CommonSQLClient, BigQueryClient, MongoDBClient] = None
    db_type: DatabaseTypes

    def text_based_schema(self):
        schema = self.client.get_schema()
        text = "Database Type: Postgres\n\n"
        for table in schema.tables:
            text += f"Table Name: {table.name}\n"
            text += "Columns:\n"
            for column in table.columns:
                text += f"  - {column.name}: {column.type}\n"
            text += "Primary Key: " + ", ".join(table.primary_keys) + "\n"
            if 'foreign_keys' in table:
                text += "Foreign Keys:\n"
                for fk in table.foreign_keys:
                    for relation in fk.relations:
                        text += f"  - {relation.column} references {relation.referenced_table}({relation.referenced_column})\n"
            text += "\n\n"
        return text

    # @staticmethod
    # async def run_call(agent: AgentExecutor, query: str, stream_it: AsyncCallbackHandler):
    #     # assign callback handler
    #     agent.agent.llm_chain.llm.callbacks = [stream_it]
    #     # now query
    #     await agent.acall(inputs={"input": query})

    # @staticmethod
    # async def create_gen(query: str, stream_it: AsyncCallbackHandler):
    #     task = asyncio.create_task(SQLAgent.run_call(query, stream_it))
    #     async for token in stream_it.aiter():
    #         yield token
    #     await task

    async def ask_langchain_agent(self, model: ModelInstance, question: str,
                                  stream: bool = False, engine=None):
        pass
        # db = None
        # common_sql_types = [DatabaseTypes.POSTGRESQL, DatabaseTypes.MYSQL, DatabaseTypes.ORACLE, DatabaseTypes.SQLITE]
        # if self.db_type in common_sql_types:
        #     db = SQLDatabase.from_uri(database_uri=self.client.get_uri())
        #     print(f"DB Initialized {db}", )
        # elif self.db_type == DatabaseTypes.BIGQUERY:
        #     print("Starting chain with BigQuery")
        #     db = SQLDatabase(engine=engine)
        #
        # llm = ChatOpenAI(model=model.name, api_key=model.api_key, temperature=0, streaming=stream)
        #
        # agent = create_sql_agent(llm=llm, db=db, agent_type="tool-calling",
        #                          verbose=True, max_iterations=30)
        # chain = create_sql_query_chain(llm, db)
        # print(f"Chain Prompt: {chain.get_prompts()[0].pretty_print()}")
        # ts_db_prompt = database_agent_promptgen("MYSQL", 10)
        # print(f"TS DB Prompt: {ts_db_prompt}")
        # prompted_question = f"{ts_db_prompt} \n {question} .Make sure the output is in proper markdown format."
        # request_inputs = {
        #     "input": prompted_question,
        # }
        #
        # if stream:
        #     stream_processor = StreamChunkProcessor()
        #     stream_outputs = agent.astream(request_inputs)
        #     async for chunk in stream_processor.process_stream(stream_outputs):
        #         if isinstance(chunk, StreamOutput):
        #             chunk_output = chunk.output
        #             chunk.output = ''
        #             chunk.streaming_complete = False
        #             chunk_size = 10  # Adjust this value to control the chunk size
        #             for i in range(0, len(chunk_output), chunk_size):
        #                 new_chunk = chunk_output[i:i + chunk_size]
        #                 chunk.output += new_chunk
        #                 is_last_chunk = i + chunk_size >= len(chunk_output)
        #                 chunk.streaming_complete = is_last_chunk
        #                 yield chunk
        #         yield chunk
        # else:
        #     with get_openai_callback() as cb:
        #         response = await agent.ainvoke(request_inputs)
        #         output = response["output"]
        #         response_data = {"input": question, "output": output, "stats": {"total_tokens": cb.total_tokens,
        #                                                                           "prompt_tokens": cb.prompt_tokens,
        #                                                                           "completion_tokens": cb.completion_tokens,
        #                                                                           "total_cost": cb.total_cost}}
        #         print("Agent Response: ", response_data)
        #         yield response_data
