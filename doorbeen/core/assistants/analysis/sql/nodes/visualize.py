from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.query.visualize import QueryVisualizationGenerator
from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.exceptions.visualizations import NoDataToPopulateVisualizations
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel


class QueryVisualizationNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        is_last_execution_failed = state.last_execution_failed is not None and state.last_execution_failed
        assert not is_last_execution_failed, "Result should be present in the state"
        connection: CommonSQLClient = configuration.get("connection", None)
        visualizer = QueryVisualizationGenerator(handler=self.handler, state=state, db_client=connection)
        viz_plan = await visualizer.plan()
        try:
            viz_with_data = await visualizer.populate_data(viz_plan)
        except NoDataToPopulateVisualizations:
            viz_with_data = viz_plan
        output = {
            "messages": [
                AIMessage(content=viz_with_data.json())
            ],
            "query_viz": viz_with_data
        }
        return output