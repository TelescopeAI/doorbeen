import uuid

from langchain_core.runnables import RunnableConfig

from core.assistants.analysis.sql.query.generate import QueryGenerator
from core.assistants.analysis.sql.state import SQLAssistantState
from core.connections.clients.SQL.common import CommonSQLClient
from core.types.ts_model import TSModel


class SQLToolkitNode(TSModel):
    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        assert state.should_enrich, "Only enrich if the state should be enriched"
        assert state.grade is not None, "Grade should be present in the state"
        connection: CommonSQLClient = configuration.get("connection", None)
        db_schema = connection.get_schema().json()
        selected_tables = connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas = connection.get_schema()
        query_generator = QueryGenerator(handler=self.handler, client=connection)
        generated_query = await query_generator.build_query(state.interpretation, selected_tables, table_schemas)
        output = {
            "messages": [
                {
                    "content": generated_query,
                    "tool_calls": [
                        {
                            "name": "generate_sql_query",
                            "args": {"input": state.input, "selected_tables": selected_tables},
                            "id": str(uuid.uuid4()),
                        }
                    ]
                }
            ],
            "generated_query": generated_query
        }
        return output