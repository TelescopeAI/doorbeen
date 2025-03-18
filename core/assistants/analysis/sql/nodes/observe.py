from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from core.assistants.analysis.sql.query.analysis import QueryResultsAnalysis
from core.assistants.analysis.sql.state import SQLAssistantState
from core.models.provider import ModelHandler
from core.types.ts_model import TSModel


class ObserveSQLResultsNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        is_last_execution_failed = state.last_execution_failed is not None and state.last_execution_failed
        assert not is_last_execution_failed, "Result should be present in the state"
        analyzer = QueryResultsAnalysis(handler=self.handler, results=state.execution_results[-1], state=state)
        report = await analyzer.analyse()
        result_message = AIMessage(
            content=report.model_dump_json(),
        )
        output = {
            "messages": [result_message],
            "query_observation_report": report
        }
        return output
