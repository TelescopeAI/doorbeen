import json
from typing import Optional

from langchain_core.messages import SystemMessage, AIMessage
from pydantic import model_validator

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.execute import ExecutionResults
from doorbeen.core.types.observe import QueryAnalysisReport, QueryEvaluationReport
from doorbeen.core.types.ts_model import TSModel


class QueryResultsContext(TSModel):
    all: list
    trimmed: Optional[list] = []
    query: Optional[str] = None

    def format_trimmed_results(self):
        row_count = len(self.all)
        formatted_text = f"""
        Query: {self.query}
        Total Rows: {row_count}
"""
        if row_count > 0:
            formatted_text += f"Rows: \n"
        # Get all row data in dict format
        for result in self.trimmed:
            result_dict = result._asdict()
            formatted_text += f"{result_dict}\n"
        return formatted_text


class QueryResultsAnalysis(TSModel):
    handler: ModelHandler
    results: ExecutionResults
    state: SQLAssistantState
    context_row_threshold: Optional[int] = 20
    _results_context: Optional[QueryResultsContext] = None
    _query_effectiveness: Optional[QueryEvaluationReport] = None

    @model_validator(mode='after')
    @classmethod
    def validate_results(cls, values):
        row_count = len(values.results.result)
        query = values.state.execution_results[-1].query
        if row_count > 0:
            values._results_context = QueryResultsContext(all=values.results.result, query=query)
        elif row_count == 0:
            values._results_context = QueryResultsContext(all=[], query=query)
        return values

    async def analyse(self):
        needs_trim = self.needs_trim()
        if needs_trim:
            await self.trim_results()
        else:
            self._results_context.trimmed = self.results.result
        report = await self.observe()
        return report

    def needs_trim(self):
        row_count = len(self.results.result)
        if row_count > self.context_row_threshold:
            return True
        return False

    async def trim_results(self):
        if self._results_context is not None and len(self._results_context.all) > 0:
            self._results_context.trimmed = self._results_context.all[:self.context_row_threshold]
        elif self._results_context is not None and len(self._results_context.all) == 0:
            self._results_context.trimmed = []

    async def evaluate_query_effectiveness(self):
        query = self.state.execution_results[-1].query
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        system_prompt = """
You are a Data Scientist who was tasked with an objective. Based on the objective, you've generated a query.
Now it's time to figure out whether this query was effective in providing the necessary data to meet the objective.

### Items provided to you:
1. **Objective**: This clearly states what the user aims to achieve (e.g., "Increase customer retention by 10%",
              "Identify top-selling products in the North American region").
2. **Query**: The SQL query that you have executed.

### Instructions:
1. **Evaluate Query Effectiveness**: Assess whether the query was effective in providing the necessary data to meet the
        objective.
2. **Explain Your Evaluation**: Provide a brief explanation of why you think the query was or was not effective. If the
objective has been met, provide explanations about why the query was effective in meeting the objective in the 
met_reasons parameter. Else provide reasons why it failed to meet expectations in the unmet_reasons parameter. Make 
sure the reasons are short but succinct. Also mention how should the query be altered to meet the objectives. 

### JSON Output Format:
Always provide your observations in the following JSON format:

{
    "query_effective": <Was the query effective in providing the necessary data to meet the objective? Yes or No>,
    "met_reasons": ["Reason 1 ", "Reason 2", ...],
    "unmet_reasons": ["Reason 1 ", "Reason 2", ...],
}
        """
        context_prompt = f"""
[OBJECTIVE]: {self.state.interpretation.objective}

[GENERATED QUERY]: {query}
        """
        messages = [
            SystemMessage(content=system_prompt),
            AIMessage(content=context_prompt)]
        response = json_llm.invoke(messages)
        response = json.loads(response.content)
        response = QueryEvaluationReport(**response)
        return response

    async def observe(self):
        query = self.state.execution_results[-1].query
        query_effectiveness = await self.evaluate_query_effectiveness()
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        system_prompt = """
You are a Data Scientist who was tasked with an objective. Now you've analysed the data but now it's
time to understand if we have done all the analysis needed to meet the objective or do we need to do more.
Also it's time to understand the results and get insights from the result.

### Items provided to you:
1. **Objective**: This clearly states what the user aims to achieve (e.g., "Increase customer retention by 10%",
              "Identify top-selling products").
2. **Results**: The data that you have got after running the query which may include numerical results,
            or summaries.
3. **Is Result Trimmed**: If the result is trimmed, it means that the result is too large to display in one go. 

### Instructions:
1. **Evaluate Objectives**: Assess whether the stated objectives have been met based on the results provided.
2. **Extract Insights**: If the objectives are met, summarize key learnings from the data. If not, identify what 
     additional analysis or data is needed. In case if there are zero results, mention that there are no results so 
     no insights can be drawn.
3. **Identify Limitations**: Discuss any limitations in the analysis or data quality that may affect the conclusions.
    If the results has been trimmed, mention that it's not possible to concur so it needs further analysis as one of 
    the limitations along with the rest.
4. **Next Steps**: Suggest actionable next steps to address unmet objectives or to further explore the insights gained.

### Examples of Insights:
- "The average customer age across all categories is 26 years, indicating a young customer base."
- "Sales in the Kitchen Accessories category are significantly higher than in others, suggesting a strong market
   demand."
- "The revenue comparison over two months shows consistent values, indicating potential data entry errors or lack
   of sales activity."

### JSON Output Format:
Always provide your observations in the following JSON format:
{
    "all_objectives_met": <Have all the objectives been met>,
    "some_objectives_met": <Is some of the objectives been met>,
    "insights" : [<Insight 1>, <Insight 2>, ...],
    "unmet_objectives": [<Objective 1>, <Objective 2>, ...],
    "next_step": "The next step you need to take to meet all the objectives",
"""
        context_prompt = f"""
[OBJECTIVE]: {self.state.interpretation.objective}

[GENERATED QUERY]: {query}

[RESULTS]: 
{self._results_context.format_trimmed_results()}
        """
        summarized_content = self.state.summary
        summarized_context = AIMessage(content=f"Here is a summary of all of the previous "
                                               f"conversations\n\n {summarized_content}\n\n")
        request_message = [
            summarized_context,
            SystemMessage(content=system_prompt),
            AIMessage(content=context_prompt)
        ]
        response = json_llm.invoke(request_message)
        response = json.loads(response.content)
        results_trimmed = self.needs_trim()
        response = QueryAnalysisReport(**response, results_trimmed=results_trimmed, query=query_effectiveness)
        return response

    async def generate_report(self):
        pass
