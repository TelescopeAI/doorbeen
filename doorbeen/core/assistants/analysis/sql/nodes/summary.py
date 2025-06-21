import json
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel


class SummarizeConversationNode(TSModel):
    handler: ModelHandler = None

    def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        messages_length = len(state.messages)
        is_messages_empty = messages_length == 1 and isinstance(state.messages[0], HumanMessage)
        connection: CommonSQLClient = configuration.get("connection", None)
        summary: str = "-------- NEW MESSAGE STARTS HERE --------\n"
        request_count = state.request_count
        summary += f"Message Count: {request_count}\n"
        summary += f"The user asked the following question:\n {state.input}\n"
        grade_summary = state.grade.model_dump_json()
        summary += f"This is how we graded the question: {grade_summary}\n"

        print(summary)
        # Use schema from state instead of reloading
        selected_tables = state.selected_tables or connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas = state.table_schemas or connection.get_schema()
        
        output = {
            "messages": [
                AIMessage(
                    content=json.dumps(summary),
                )
            ],
            "input": self.qn,
            "is_followup": state.is_followup,
            "selected_tables": selected_tables,
            "table_schemas": table_schemas
        }

        return output


class DetermineInputObjectives(TSModel):
    llm: Optional[Any] = None

    def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        return state
