from typing import Optional

from langchain_core.runnables import RunnableConfig

from core.assistants.analysis.sql.state import SQLAssistantState
from core.models.provider import ModelHandler
from core.types.ts_model import TSModel


class SQLAnalysisEntryNode(TSModel):
    handler: ModelHandler = None

    def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        self.state = state
        self.state.input = self.question
        return state

    def should_continue(self, state: Optional[SQLAssistantState]):
        messages = state.messages
        # If there is no function call, then we finish
        if state.qa_passed:
            return "end"
        # If tool call is asking Human, we return that node
        # You could also add logic here to let some system know that there's something that requires Human input
        # For example, send a slack message, etc
        else:
            return "continue"
