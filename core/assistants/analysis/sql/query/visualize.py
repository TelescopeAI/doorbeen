import json
from typing import Optional

from pydantic import Field

from core.assistants.analysis.sql.state import SQLAssistantState
from core.models.provider import ModelHandler
from core.types.ts_model import TSModel
from core.types.visualize import QueryVisualizationPlan, VizWithData


class QueryVisualizationGenerator(TSModel):
    handler: ModelHandler
    state: SQLAssistantState
    visualization_plan: Optional[QueryVisualizationPlan] = Field(default_factory=QueryVisualizationPlan, description="")

    def format_results_for_model(results: list):
        formatted_text = ""
        for result in results:
            result_dict = result._asdict()
            formatted_text += f"{result_dict}\n"
        return formatted_text

    def get_column_count(self, result):
        result_dict = result._asdict()
        key_count = len(result_dict.keys())
        return key_count

    async def get_results_meta(self):
        result = self.state.execution_results[-1].result
        row_count = len(result)
        column_count = self.get_column_count(result[0]) if row_count > 0 else 0
        return {
            "row_count": row_count,
            "column_count": column_count
        }

    async def gen_visualizations(self):
        query = self.state.execution_results[-1].query
        series = []
        system_prompt = """
You are an expert in generating data visualizations for any SQL Query. The first step is to understand whether
the query needs visualizations or not. If the output of the query is likely to generate one concrete value then
it does not need visualizations. However, if the output is likely to generate multiple values then it needs 
visualizations.

The second step is to figure out what kind of chart can be used to represent the data. You can choose a chart type from
the following list:
1. Line Chart (code: 'line')
2. Bar Chart (code: 'bar')
3. Pie Chart (code: 'pie')

The third step is to find out the series & categories that can be generated from the query. 
A series is a collection of data points i.e, it's the values from one particular column. 
For example, if you have a column named 'age' then the series would be the collection of all the ages. 
If there are multiple columns then there would be multiple series.

A category is a collection of data points that are used to differentiate between the series. For example, if you have
4 different columns Name, Age, Salary, Order Value then the values for Name would be the categories and the values for
Age, Salary, Order Value would be the series. 

Series represents y-axis and and category defines the x-axis of the chart.

You'll have to refactor the query to get the datapoints for each series and categories. If there are 0 rows and columns,
then the query does not need visualizations.

Items Provided to you:
1. Result Metadata: You'll have access to how many records are returned by the query and if there are multiple columns
present.
2. Query: The SQL Query that was executed.

### JSON Output Format:
Always provide your observations in the following JSON format:

{
    "needs_visualization": <Does this require visualization?>,
    "chart_type": <Type of Chart>,
    "series": [
    {
        "name": <Series Name>,
        "query": <Refactored Query to get the series data. [IMPORTANT] Make sure this selects only one column>
    },
    "categories": {
        "name": <Category Name>,
        "query": <Refactored Query to get the category data. [IMPORTANT] Make sure this selects only one column>
    },
     
     
    ...
    ]
}
"""
        context_prompt = f"""
        [GENERATED QUERY]: {query}
        [Results Metadata]: {await self.get_results_meta()}
                """

        messages = [
            system_prompt,
            context_prompt
        ]
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = json_llm.invoke(messages)
        response = json.loads(response.content)
        self.visualization_plan = QueryVisualizationPlan(**response)
        return self.visualization_plan

    async def insert_data(self):
        viz_plan = self.visualization_plan
        if viz_plan:
            # For each of the series, run the query and extract the data points
            # Do the same for each of the categories, run the query and extract the data points
            series = viz_plan.series
            categories = viz_plan.categories
            series_data = []
            categories_data = []
            for series_item in series:
                series_query = series_item.query
                series_data.append(await self.state.client.execute_query(series_query))
            for category in categories:
                categories_data.append(await self.state.client.execute_query(category.query))

            return VizWithData(series=series_data, categories=categories_data)

