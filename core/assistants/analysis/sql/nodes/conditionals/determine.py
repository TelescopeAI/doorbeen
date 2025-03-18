import json
import uuid
from enum import Enum
from logging import info
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from core.assistants.analysis.sql.state import SQLAssistantState
from core.connections.clients.SQL.common import CommonSQLClient
from core.models.provider import ModelHandler
from core.types.ts_model import TSModel


class DeterminedQuestionTypes(Enum):
    NEW = "new"
    FOLLOWUP = "followup"


class InitAssistant(TSModel):
    handler: ModelHandler = None
    qn: Optional[str] = None

    def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        messages_length = len(state.messages)
        is_messages_empty = messages_length == 1 and isinstance(state.messages[0], HumanMessage)
        connection: CommonSQLClient = configuration.get("connection", None)
        print("Starting SQL Analysis. Entry Node is initialized.")
        print(f"Connection: {connection}")
        print(f"Thread ID: {configuration.get('thread_id')}")
        print(f"Table Names: {connection.get_table_names(schema_name=connection.credentials.database)}")
        print(f"Schema: {connection.get_schema()}")
        determined_type = {"question_type": None}
        if is_messages_empty:
            determined_type["question_type"] = DeterminedQuestionTypes.NEW.value
        else:
            determined_type["question_type"] = DeterminedQuestionTypes.FOLLOWUP.value

        state.is_followup = True if determined_type[
                                        "question_type"] == DeterminedQuestionTypes.FOLLOWUP.value else False
        state.request_count += 1
        summary = "" if state.summary is None else state.summary
        summary += "\n\n------------------------- [New Message Starts Here] -------------------------\n"
        summary += f"This is the order of the message: {state.request_count}\n"
        output = {
            "messages": [
                AIMessage(
                    content=json.dumps(determined_type),
                    name="init_assistant"
                )
            ],
            "request_count": state.request_count,
            "input": self.qn,
            "is_followup": state.is_followup,
            "selected_tables": connection.get_table_names(schema_name=connection.credentials.database),
            "table_schemas": connection.get_schema(),
            "summary": summary
        }

        return output


class DetermineInputObjectives(TSModel):
    llm: Optional[Any] = None

    def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        return state
