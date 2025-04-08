from typing import List, Dict, Any

from pydantic import Field

from doorbeen.core.assistants.analysis.sql.query.understanding import QueryUnderstanding
from doorbeen.core.assistants.hooks.callback import CallbackManager
from doorbeen.core.models.invoker import ModelInvoker
from doorbeen.core.models.model import ModelInstance
from doorbeen.core.models.provider import ModelProvider
from doorbeen.core.types.ts_model import TSModel


class ValidationResult(TSModel):
    passed: bool = Field(description="Whether the query results passed the validation")
    explanation: str = Field(description="Explanation of the validation results")


class QueryValidationEngine(TSModel):
    model: ModelInstance

    def validate_results(self, understanding: QueryUnderstanding, query: str,
                         results: List) -> ValidationResult:
        result_count = len(results)
        if result_count == 0:
            return ValidationResult(passed=False, explanation="No results were returned")
        elif 0 < result_count < 5:
            test_set = results
        else:
            # Select top 3 results and 2 random rows for the test set
            test_set = results[:3] + (results[3:5] if result_count > 5 else results[3:])

        prompt = f"""
        Validate the following query results against the original query objective and tests:

        Objective: {understanding.objective}
        Tests: {understanding.tests}

        Query:
        {query}

        Results (sample):
        {self._format_results(test_set)}

        Evaluate if the query results meet the objective and pass the specified tests.
        Your response should be in the following JSON format:
        {{
            "passed": true/false,
            "explanation": "Detailed explanation of whether the results meet the objective and pass the tests"
        }}
        """

        llm = ModelProvider().get_model_instance(model_name=self.model.name, api_key=self.model.api_key,
                                                 output_model=ValidationResult)
        with CallbackManager.get_callback(self.model.provider, self.model.name) as cb:
            response = ModelInvoker(llm=llm).process(prompt=prompt, output_model=ValidationResult)

            if hasattr(cb, 'update'):
                cb.update(response)

        # Parse the JSON response and create a ValidationResult object
        validation_result = ValidationResult(**response.json())
        return validation_result

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        formatted_results = ""
        for i, row in enumerate(results, 1):
            formatted_results += f"Row {i}:\n"
            for key, value in row.items():
                formatted_results += f"  {key}: {value}\n"
            formatted_results += "\n"
        return formatted_results
