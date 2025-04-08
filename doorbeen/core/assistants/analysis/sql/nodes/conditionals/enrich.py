import json
import uuid

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.prompts.inputs.enrich import enrich_input
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.enrich import EnrichedOutput
from doorbeen.core.types.ts_model import TSModel


class EnrichInputNode(TSModel):
    handler: ModelHandler = None

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        assert state.should_enrich, "Only enrich if the state should be enriched"
        assert state.grade is not None, "Grade should be present in the state"
        connection: CommonSQLClient = configuration.get("connection", None)
        db_schema = connection.get_schema().json()
        prompt = enrich_input(db_schema)

        user_input = f"Enrich this input:\n{state.input}\n\n{db_schema}\n\n{state.grade.json()}"
        state.messages.append(SystemMessage(content=prompt))
        state.messages.append(HumanMessage(content=user_input))
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = await json_llm.ainvoke(state.messages)
        response = json.loads(response.content)
        enriched_output = EnrichedOutput(**response)
        summary = state.summary
        summary += "\n\n[CURRENT OPERATION: Input Enrichment]\n"
        summary += f"We've decided to enrich the input and this was the result.\n"
        summary += enriched_output.model_dump_json(indent=4) + "\n"


        result_message = AIMessage(
                    content=enriched_output.model_dump_json(),
                )

        output = {
            "messages": [result_message],
            "input": enriched_output.improved_input,
            "enrich_output": enriched_output
        }
        return output
