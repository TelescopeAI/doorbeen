import json
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from core.assistants.analysis.sql.state import SQLAssistantState
from core.connections.clients.SQL.common import CommonSQLClient
from core.models.provider import ModelHandler
from core.types.ts_model import TSModel


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
        output = {
            "messages": [
                AIMessage(
                    content=json.dumps(summary),
                )
            ],
            "input": self.qn,
            "is_followup": state.is_followup,
            "selected_tables": connection.get_table_names(schema_name=connection.credentials.database),
            "table_schemas": connection.get_schema()
        }

        return output


class DetermineInputObjectives(TSModel):
    llm: Optional[Any] = None

    def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        return state
