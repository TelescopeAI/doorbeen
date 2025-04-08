import json
from typing import List, Optional, Union

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, field_validator

from doorbeen.core.assistants.hooks.callback import ModelCallback
from doorbeen.core.types.sql_schema import DatabaseSchema
from doorbeen.core.types.ts_model import TSModel


class QueryPlanTask(TSModel):
    name: str = Field(description="The name of the task")
    operation: str = Field(description="The operation performed by the task")
    order: int = Field(description="The order in which the task should be performed")


class QueryPlanGroup(TSModel):
    name: str = Field(description="The name of the group")
    tasks: List[QueryPlanTask] = Field(description="The tasks in the group")
    order: int = Field(description="The order in which the group should be performed")
    depends_on: Optional[int] = Field(default=None, description="The order number of the dependent group")

    @field_validator("depends_on", mode="before")
    @classmethod
    def transform_if_none(cls, v):
        if v == 'None' or v is None:
            return None
        else:
            return int(v)


class QueryPlan(TSModel):
    groups: List[QueryPlanGroup] = Field(description="The groups of tasks in the plan")


class QueryUnderstanding(TSModel):
    objective: str = Field(description="What the user wants to achieve")
    plan: QueryPlan = Field(description="The high-level plan to achieve the objective")
    reasoning: str = Field(description="How to achieve the objective using available data")
    tests: List[str] = Field(description="Tests to validate if the output meets the objective")
    operations: List[str] = Field(description="Common operations to perform on the data to achieve the objective")


class QueryUnderstandingEngine(TSModel):
    llm: Optional[Union[ChatOpenAI]] = None
    cb_manager: Optional[ModelCallback] = None

    async def get_prompt(self, question: str, selected_tables: List[str],
                         table_schemas: DatabaseSchema):
        prompt = f"""
        Analyze the following user question and table schemas to understand the query requirements:

        User Question: {question}

        Table Schemas:
        {self._format_schema_info(table_schemas)}

        Selected Tables: {', '.join(selected_tables)}
        
        The following data sources can be used to understand the query requirements. There are 3 types of Data Sources 
        which are Internal Database, API Integrations, Web Search.
        Check below to find out which data sources are available.
        
        [Available Data Sources]
        - INTERNAL_DATABASE
        
        [Grouping Guidelines]
        - Always group tasks that can be done in one step.
        - A step is a SQL operation that can be executed in one go.
        - For example, selecting, filtering, sorting, grouping and joining can be done in one step.
        - Grouping by any of the columns or multiple columns can also be done in one step.
        - Even if the operation is complex, if it can be done in one step, group it together.
        - Ideally the only time you should create a new group is when you have to change the data source that's 
          available to you. Only create more than one groups if you are absolutely sure that it cannot be done in 
          one step because otherwise it'll likely leads to errors.
        - If you think the question is little vague then you can assume that the user is asking for the top 10 results.
          Ignore this instruction if the user has mentioned the number of results they want.
        

        Provide the following:
        1. Objective: What does the user want to achieve?
        2. Reasoning: Based on the objective, which columns should be selected? Should they be grouped/sorted/both 
                      (if yes, then in which order)? Is there a requirement for joins (if yes, how should the joins work)?
        3. Planning: What is the high-level plan to achieve the objective?
                     Break down the plan into individual tasks. Tasks can be grouped based on the operation they 
                     perform. [STRICT] Always stick to the grouping guidelines.
        4. Tests: A set of tests that can be used to evaluate if the output met the objective. 
                  Each test should be realistic(can be executed using SQL) and should be able to validate the
                  output based on the schema provided only.
        5. Operations: What common operations should be performed on the data to achieve the objective? Mention the
                       column names and the operations that should be performed on them.
                       For example, grouping by a column, sorting by a column, filtering by a column, etc. 

        Your response should be in the following JSON format:
        {{
            "objective": "Clear statement of what the user wants",
            "plan": {{
                "groups":[
                    {{
                        "name": "<Short Group Name>",
                        "order": "<The order in which the group operations should be executed>"
                        "depends_on": "<None or the order number of the dependant group>"
                        "tasks": [{{
                            "name": "<Task 1 Name>",
                            "operation": "<Operation(Explain in depth as much as required. Not too short nor long)>",
                            "order": <Order Number>
                        }},
                        ...,
                        ...,
                        ]
                    }},
                    ...
                ],
                }},
            "reasoning": "Detailed explanation of how to achieve the objective using the available data",
            "tests": ["<Test 1>", "<Test 2>", ...],
            "operations": ["<Operation 1>", "<Operation 2>", ...]
        }}
        """
        message = SystemMessage(content=prompt)

        return message

    def _format_schema_info(self, database_schema: DatabaseSchema) -> str:
        schema_info = ""
        for table in database_schema.tables:
            schema_info += f"Table: {table.name}\n"
            for column in table.columns:
                schema_info += f"  - {column.name}: {column.type}\n"
            schema_info += "\n"
        return schema_info
