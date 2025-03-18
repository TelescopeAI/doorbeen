from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from core.assistants.analysis.sql.query.generate import QueryGenerator
from core.assistants.analysis.sql.state import SQLAssistantState
from core.connections.clients.SQL.common import CommonSQLClient
from core.models.provider import ModelHandler
from core.types.generate import GeneratedSQLQuery
from core.types.ts_model import TSModel


class GenerateSQLQueryNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection", None)
        selected_tables = connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas = connection.get_schema()
        query_generator = QueryGenerator(handler=self.handler, client=connection)
        built_query = await query_generator.build_query(state.interpretation, selected_tables, table_schemas, state)
        generated_query = GeneratedSQLQuery(**built_query.content)

        result_message = AIMessage(
            content=generated_query.model_dump_json()
        )
        summary = state.summary
        summary += "\n\n[CURRENT OPERATION: Generating SQL Query]\n"
        summary += f"Based on the current interpretation, we've generated the following SQL Query.\n"
        summary += generated_query.model_dump_json(indent=4) + "\n"

        output = {
            "messages": [
                result_message
            ],
            "generated_query": generated_query
        }
        return output
