import json

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.followups import FollowupAttempts
from doorbeen.core.types.ts_model import TSModel


class InputFollowupNode(TSModel):
    handler: ModelHandler = None

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        assert state.is_followup, "This node should only be called for follow-up inputs"
        summary = state.summary
        summary_message = SystemMessage(content=f"This is the summary of everything that has happened till now\n {summary}")
        messages = [summary_message]

        last_messages = summary_message
        # call the model and see if this can be answered based on whatever we know till now
        prompt = """You are tasked with analyzing a series of messages to determine if the current question from the 
user can be answered with the information already available.

**Instructions:**

1. Review the summary of all the previous messages to understand the context and information already known.
2. Determine if the current question can be fully answered with this information.
3. Look for signs if this question has been asked before and look for the messages after that to find out the previous answers.
3. Provide a JSON output with the following structure:
   - "answer": The answer to the question if it can be fully answered, otherwise provide context or partial information.
   - "is_related:": A boolean value indicating if the question is related to the previous question.
   - "certainty_level": A value indicating the level of certainty in the answer. Use "full" if the question is fully answered, or "partial" if additional information is needed. If you are unsure, use "unsure".
   - "modified_question": If the question is not fully answered, suggest a modification to the question so that we can gather the necessary information while keeping the original question in mind.

**Output Format:**

{
    "answer": "<Your answer or context here>",
    "is_related": "<true/false>",
    "certainty_level": "<full/partial/unsure>",
    "modified_question": "<Modified question if needed or else the original question>"
}
"""
        messages.append(SystemMessage(content=prompt))
        messages.append(HumanMessage(content=f"CURRENT QUESTION:\n {state.input}"))
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = await json_llm.ainvoke(messages)
        response = json.loads(response.content)
        response = FollowupAttempts(**response)
        result_message = AIMessage(
            content=response.model_dump_json(),
        )
        summary = state.summary
        summary += f"Is this related to the previous question: {'Yes' if state.is_followup else 'No'}\n"



        dont_modify_input = response.certainty_level == "unsure"
        output = {
            "messages": [result_message],
            "input":  state.input,
            'is_followup': response.is_related or state.is_followup,
            "summary": summary,

        }
        print(f"Follow-up question: {response.modified_question}")
        return output
