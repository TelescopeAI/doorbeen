import json
import uuid

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from core.assistants.analysis.sql.state import SQLAssistantState
from core.assistants.prompts.inputs.grader import grade_question
from core.connections.clients.SQL.common import CommonSQLClient
from core.models.provider import ModelHandler
from core.types.ts_model import TSModel


class InputGradingNode(TSModel):
    handler: ModelHandler = None

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection", None)
        db_schema = connection.get_schema()
        prompt = grade_question(db_schema)
        summarized_content = state.summary
        summarized_context = AIMessage(content=f"Here is a summary of all of the previous "
                                               f"conversations\n\n {summarized_content}\n\n")
        request_messages = [
            summarized_context,
            SystemMessage(content=prompt),
            AIMessage(content=state.input)
        ]
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = await json_llm.ainvoke(request_messages)
        response = json.loads(response.content)
        should_enrich = response.get("should_enrich", False)
        summary = state.summary
        summary += (f"After evaluating the question based on various parameters, we determined that these are the"
                    f" grades:\n")
        summary += json.dumps(response, indent=4) + "\n"
        result_message = AIMessage(
                    content=json.dumps(response),
                )
        output = {
            "messages": [result_message],
            "should_enrich": False,
            "grade": response,
            "summary": summary
        }
        state.qa_passed = True
        return output

