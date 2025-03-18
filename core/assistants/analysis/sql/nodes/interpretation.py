import json

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from core.assistants.analysis.sql.query.understanding import QueryUnderstandingEngine, QueryUnderstanding
from core.assistants.analysis.sql.state import SQLAssistantState
from core.connections.clients.SQL.common import CommonSQLClient
from core.models.provider import ModelHandler
from core.types.ts_model import TSModel


class InterpretInputNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        assert state.grade is not None, "Grade should be present in the state"
        connection: CommonSQLClient = configuration.get("connection", None)
        db_schema = connection.get_schema().json()
        selected_tables = connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas = connection.get_schema()
        prompt_message = await QueryUnderstandingEngine(llm=self.handler.model).get_prompt(state.input,
                                                                                           selected_tables,
                                                                                           table_schemas)
        summarized_content = state.summary
        summarized_context = AIMessage(content=f"Here is a summary of all of the previous "
                                               f"conversations\n\n {summarized_content}\n\n")
        request_messages = [
            summarized_context,
            prompt_message
        ]

        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = await json_llm.ainvoke(request_messages)
        response = json.loads(response.content)
        interpretation = QueryUnderstanding(**response)

        summary = state.summary
        summary += "\n\n[CURRENT OPERATION: Interpretation]\n"
        summary += f"This is our current interpretation of the input based on the available information.\n"
        summary += interpretation.model_dump_json(indent=4) + "\n"

        result_message = AIMessage(
            content=interpretation.model_dump_json(),
        )
        output = {
            "messages": [result_message],
            "interpretation": interpretation,
            "summary": summary
        }
        return output
