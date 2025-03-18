from typing import List, Dict, Any, Optional

import pandas as pd
from pydantic import Field

from core.assistants.analysis.sql.query.attempt import QueryExecutionAttempt
from core.assistants.analysis.sql.query.errors import AttemptErrorDetails
from core.assistants.analysis.sql.query.planner import QueryPlan, QueryPlanningEngine
from core.assistants.analysis.sql.query.results import QueryResult
from core.assistants.analysis.sql.query.understanding import QueryUnderstanding, QueryUnderstandingEngine
from core.assistants.analysis.sql.query.validation import ValidationResult, QueryValidationEngine
from core.connections.clients.base import DatabaseClient
from core.exceptions.SQLClients import CSQLInvalidQuery, QueryValidationFailed
from core.models.model import ModelInstance
from core.types.sql_schema import ColumnSchema
from core.types.ts_model import TSModel


class QueryExecutor(TSModel):
    client: Any = Field(description="Database client")

    def execute_query(self, query: str) -> QueryResult:
        # Execute the query using your client's method
        # This is just an example, adjust according to your client's API
        result = self.client.query(query)
        df = pd.DataFrame(result)
        return QueryResult(data=df.to_dict())


class QueryExecutionResult(TSModel):
    understanding: QueryUnderstanding
    plan: QueryPlan
    results: List[Dict[str, Any]]
    validation: ValidationResult


class QueryExecutionManager(TSModel):
    model: ModelInstance
    understanding_engine: QueryUnderstandingEngine
    planning_engine: QueryPlanningEngine
    validation_engine: QueryValidationEngine
    client: DatabaseClient
    attempts: Optional[List[QueryExecutionAttempt]] = None


    def gen_error_summary(self) -> str:
        error_summary = "[Error Summary]\n"
        for attempt in self.attempts:
            error_summary += f"Attempt Number: {attempt.number}\n"
            error_summary += f"Query: {attempt.error.query}\n"
            error_summary += f"Logic: {attempt.error.logic}\n"
            error_summary += f"Error: {attempt.error.message}\n\n"
        return error_summary

    def _attempt_(self, question: str, selected_tables: List[str],
                  table_schemas: Dict[str, List[ColumnSchema]],
                  previous_attempts: Optional[List[QueryExecutionAttempt]] = None):

        #Step 0: If there previous attempts, check the attempt and format the error summary that should be added to the question
        previous_error_summary = ""

        if previous_attempts and len(previous_attempts) > 0:
            self.attempts = previous_attempts
            print(f"Starting Attempt No: {len(previous_attempts) + 1}")
            previous_error_summary = self.gen_error_summary()
            print(f"Previous Error Summary: ", previous_error_summary)
        else:
            print(f"Starting Attempt No: 1")

        # Step 1: Understand the query
        understanding = self.understanding_engine.get_prompt(question, selected_tables, table_schemas)
        print(f"Understanding: {understanding.model_dump_json(indent=4)}")

        # Step 2: Plan the query
        plan = self.planning_engine.generate_query(understanding, table_schemas, previous_error_summary)
        print(f"Plan: {plan.model_dump_json(indent=4)}")

        # Step 3: Execute the query
        query_error = None
        try:
            results = self.client.query(sql=plan.query)
        except CSQLInvalidQuery as e:
            results = []
            query_error = e
        print(f"Results: {results}")

        # Step 4: Validate the results

        validation = self.validation_engine.validate_results(understanding,
                                                             plan.query,
                                                             results)
        print(f"Validation: {validation.model_dump_json(indent=4) if validation is not None else None}")
        return understanding, plan, results, validation, query_error

    def execute_query(self, question: str, selected_tables: List[str],
                      table_schemas: Dict[str, List[ColumnSchema]],
                      last_attempt: int = 0,
                      max_attempts: int = 10,
                      previous_attempts: Optional[List[QueryExecutionAttempt]] = None
                      ) -> QueryExecutionResult:
        understanding, plan, results, validation, query_error = None, None, [], None, None
        try:
            understanding, plan, results, validation, query_error = self._attempt_(question,
                                                                                   selected_tables,
                                                                                   table_schemas,
                                                                                   previous_attempts)
            if validation.passed:
                previous_attempts.append(
                    QueryExecutionAttempt(
                        number=last_attempt + 1,
                        success=True,
                        results=results
                    )
                )
                return QueryExecutionResult(
                    understanding=understanding,
                    plan=plan,
                    results=results,
                    validation=validation
                )
            else:
                previous_attempts = previous_attempts if previous_attempts else []
                previous_attempts.append(
                    QueryExecutionAttempt(
                        number=last_attempt + 1,
                        success=True,
                        results=results
                    )
                )
                raise QueryValidationFailed(validation)
        except (CSQLInvalidQuery, QueryValidationFailed):
            error_message = query_error.message if query_error else validation.explanation
            attempt_error = AttemptErrorDetails(
                query=plan.query if plan.query else "Couldn't generate query this time",
                logic=plan.explanation if plan.explanation else "Couldn't generate explanation this time",
                message=error_message
            )
            execution_attempt = QueryExecutionAttempt(
                number=last_attempt + 1,
                success=False,
                error=attempt_error
            )
            previous_attempts.append(execution_attempt)
            max_attempts -= 1
            self.execute_query(question, selected_tables, table_schemas, max_attempts,
                               previous_attempts=previous_attempts)
