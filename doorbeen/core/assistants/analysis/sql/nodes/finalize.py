import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.prompts.memory.summarize import SUMMARIZE_MEMORY_SYSTEM
from doorbeen.core.assistants.utils.sql import convert_sqlalchemy_rows_to_dict
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.finalize import FinalPresentation
from doorbeen.core.types.ts_model import TSModel


class FinalizeAnswerNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection", None)
        selected_tables = connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas = connection.get_schema().json()

        last_execution_results = state.execution_results[-1].result
        row_dicts = convert_sqlalchemy_rows_to_dict(last_execution_results)

        # Steps to perform here
        # 1. Fetch the query_observation_report: QueryAnalysisReport from the state
        assert state.query_observation_report is not None, "Query Observation Report should be present in the state"
        observed_report = state.query_observation_report
        # 2. Make a request to the LLM with the original question, interpretation and the observed_report to get the
        # final answer. No need to include tables because the output from the last executed sql query would be provided
        # in the result
        interpretation = state.interpretation
        original_question = state.input

        system_prompt = """
        You are a Data Scientist who was tasked with an objective. Now you've analysed the data and now it's time to
        present that to the user in a way that they can understand. You have the original question, the interpretation
        of the question and the results from the analysis of the data that you've done.
        
        **Capabilities**
        1. You can run more queries given the tables that you have.
        
        **Instructions**
        1. Verify that the interpretation of the original question is correct. If it's correct always answer in a manner
        that the is a good answer for that interpretation
        2. Verify that the analysis of the data has been completed. all_objectives_met should be True if we are ready
           to present this data to the user. If some_objectives_met is True then look at the unmet_objectives and 
           figure out if they can be met with the list of capabilities that you have. If yes then run more queries or
           else present the data to the user.
        3. If you are ready to present the data to the user then imagine you're presenting this data to a non-technical
           person. Make sure that the data is easy to understand and the insights are clear.
        4. Do not mention anything about the items that have been presented to you. 
        5. In case if you are referring to any datapoint, make sure to use the entity name as  well. Do not use names
        like Category A, instead say <Category [Category ID]>.
           
        **JSON Output Format**
        {
            "ready_to_present": <True/False>,
            "interpretation_correct": <True/False>,
            "message": <Message to be presented to the user in markdown>
        }
"""
        context_prompt = f"""
        [ORIGINAL QUESTION]: {original_question}
        
        [INTERPRETATION]:

        {interpretation.objective}
        
        [Analysis Report]: {observed_report.model_dump_json()}
        
        **Database Info Availability**:
        
        [SELECTED TABLES]: {selected_tables}
        
        [TABLE SCHEMAS]: {table_schemas}
        """

        summarized_content = state.summary
        summarized_context = AIMessage(content=f"Here is a summary of all of the previous "
                                               f"conversations\n\n {summarized_content}\n\n")
        request_messages = [
            summarized_context,
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_prompt)
        ]
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = json_llm.invoke(request_messages)
        response = json.loads(response.content)
        summarized_content += json.dumps(response) + "\n"
        response = FinalPresentation(**response, results=row_dicts)

        summarized_content += "\n\n[CURRENT OPERATION: Presenting Final Answer to the User]\n"
        summarized_content += (f"After thinking through the problem and analysing the data, you've come up with"
                               f"the following information:\n\n {summarized_content}\n\n")

        result_count = len(row_dicts)
        RESULT_SUMMARY_THRESHOLD = 30
        summarized_content += f"There are {result_count} records in the result of the executed query.\n"
        included_results = row_dicts[:RESULT_SUMMARY_THRESHOLD] if result_count > 0 else []
        if result_count > RESULT_SUMMARY_THRESHOLD:
            summarized_content += (f"The results displayed below have been trimmed due to memory limitations.\n")
        for result in included_results:
            summarized_content += json.dumps(result, indent=2) + "\n"

        summarization_messages = [
            SystemMessage(content=SUMMARIZE_MEMORY_SYSTEM),
            AIMessage(content=summarized_content)
        ]

        msg_summary = self.handler.model.invoke(summarization_messages)
        msg_summary = msg_summary.content

        result_message = AIMessage(
            content=response.model_dump_json()
        )
        output = {
            "messages": [result_message],
            "summary": msg_summary
        }
        return output

        # is_last_execution_failed = state.last_execution_failed is not None and state.last_execution_failed
        # assert not is_last_execution_failed, "Result should be present in the state"
        #
        # execution_result = state.execution_results[-1]
        # # Check how many rows are there
        # row_count = len(execution_result.result)
        # # Convert List[SQLAlchemy Row] to List[Dict]
        # data = execution_result.result
        #
        # system_prompt = f"""
        # You are a Data Scientist who was tasked with an objective. Now you've analysed the data but now it's
        # time to understand if we have done all the analysis needed to meet the objective or do we need to do more.
        #
        # Items provide to you.
        # 1. Objective
        # 2.
        #
        #
        # """
        # output = {
        #     "messages": [
        #         AIMessage(content="")
        #     ],
        # }
        # return output
