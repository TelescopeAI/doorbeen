from typing import List, Dict, Any, Optional

from pydantic import Field

from core.assistants.analysis.sql.query.executor import QueryExecutionManager, \
    QueryExecutionResult
from core.assistants.analysis.sql.state import SQLAssistantState
from core.assistants.analysis.sql.tablepicker import TableAnalyzer
from core.models.model import ModelInstance
from core.types.sql_schema import ColumnSchema
from core.types.ts_model import TSModel


class MaxRetriesExceededError(Exception):
    pass


class WorkflowResult(TSModel):
    query: str = Field(description="The generated SQL query")
    result: List[Dict[str, Any]] = Field(description="The query result")
    selected_tables: List[str] = Field(description="List of selected tables for the query")
    table_schemas: Dict[str, List[ColumnSchema]] = Field(description="Schemas of the selected tables")
    usage_stats: Dict[str, Any] = Field(default_factory=dict, description="Usage statistics for the operation")
    error_count: int = Field(default=0, description="Number of errors encountered")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    execution_result: QueryExecutionResult = Field(description="Detailed execution result")


class SQLAssistantWorkflow(TSModel):
    client: Any = Field(description="Database client")
    table_analyzer: TableAnalyzer
    query_execution_manager: QueryExecutionManager
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")

    def run_workflow(self, state: Any, schema: Optional[str] = None) -> WorkflowResult:
        usage_stats = {}
        error_count = 0
        errors = []

        available_tables = self.table_analyzer.get_available_tables(schema)
        selected_tables, table_selection_usage = self.table_analyzer.select_relevant_tables(available_tables,
                                                                                            state.input)
        usage_stats['table_selection'] = table_selection_usage

        table_schemas = {}
        for table in selected_tables:
            if table not in state.table_schemas:
                schema_info = self.table_analyzer.get_table_schema(table, schema)
                state.add_table_schema(table, schema_info)
            table_schemas[table] = state.table_schemas[table]

        for attempt in range(self.max_retries):
            try:
                execution_result = self.query_execution_manager.execute_query(state.input, selected_tables,
                                                                              table_schemas)

                return WorkflowResult(
                    query=execution_result.plan.query,
                    result=execution_result.results,
                    selected_tables=selected_tables,
                    table_schemas=table_schemas,
                    usage_stats=usage_stats,
                    error_count=error_count,
                    errors=errors,
                    execution_result=execution_result
                )
            except Exception as e:
                error_count += 1
                error_message = str(e)
                errors.append(error_message)

                if attempt == self.max_retries - 1:
                    raise MaxRetriesExceededError(
                        f"Max retries ({self.max_retries}) exceeded. Last error: {error_message}")

    def update_model(self, model: ModelInstance):
        self.current_model = model
        for component in [self.query_builder, self.table_analyzer, self.query_executor]:
            if hasattr(component, 'update_model'):
                component.update_model(model)

    def follow_up_query(self, state: SQLAssistantState) -> WorkflowResult:
        query = self.query_builder.build_query(state.input, state.selected_tables, state.table_schemas)
        result = self.query_executor.execute_query(query)

        return WorkflowResult(
            query=query,
            result=result.dict(),
            selected_tables=state.selected_tables,
            table_schemas=state.table_schemas
        )