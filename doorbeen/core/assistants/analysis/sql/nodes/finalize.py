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
        
        # CIRCUIT BREAKER HANDLING: Check if we need to provide a circuit breaker response
        if getattr(state, 'circuit_breaker_triggered', False):
            return await self._handle_circuit_breaker_response(state)
        
        # Use schema from state instead of reloading
        selected_tables = state.selected_tables or connection.get_table_names(schema_name=connection.credentials.database)
        table_schemas_json = state.table_schemas.model_dump_json() if state.table_schemas else connection.get_schema().model_dump_json()

        # Check if we have valid execution results
        if not state.execution_results or not state.execution_results[-1].result:
            return await self._handle_no_results_response(state)

        last_execution_results = state.execution_results[-1].result
        row_dicts = convert_sqlalchemy_rows_to_dict(last_execution_results)

        # Check if we have a query observation report
        if not state.query_observation_report:
            return await self._handle_minimal_response(state, row_dicts)

        # Normal flow with full data
        return await self._handle_normal_response(state, row_dicts, selected_tables, table_schemas_json)

    async def _handle_circuit_breaker_response(self, state: SQLAssistantState):
        """Handle responses when circuit breaker is triggered"""
        original_question = state.input
        interpretation = state.interpretation.objective if state.interpretation else "analyzing your question"
        
        # Collect any insights from previous attempts
        insights = []
        if state.exploration_findings:
            insights.append(f"Database exploration found: {state.exploration_findings}")
        
        if state.execution_error_history:
            insights.append(f"Encountered technical challenges with query execution after {state.retry_count} attempts")
        
        error_context = ""
        if state.execution_error_history:
            error_context = f"The last error was: {state.execution_error_history[-1]}"

        system_prompt = """
        You are a Data Scientist explaining why a query couldn't be completed and providing helpful guidance.
        The system encountered technical difficulties after multiple retry attempts (circuit breaker triggered).
        
        **Instructions**:
        1. Acknowledge the original question and explain the technical challenges encountered
        2. Provide any insights that were gathered during exploration
        3. Suggest alternative approaches or modifications to the question
        4. Be helpful and professional, not apologetic
        5. Generate 3-5 follow-up questions that might be easier to answer or approach the problem differently
        
        **JSON Output Format**:
        {
            "ready_to_present": true,
            "interpretation_correct": true,
            "message": "<Professional explanation in markdown>",
            "next_questions": [
                "Could you rephrase this question to be more specific?",
                "Would you like to explore a subset of this data first?",
                "Are there specific time periods or categories you're most interested in?"
            ]
        }
        """

        context_prompt = f"""
        [ORIGINAL QUESTION]: {original_question}
        [INTERPRETATION]: {interpretation}
        [INSIGHTS GATHERED]: {'; '.join(insights) if insights else 'Initial database exploration was completed'}
        [ERROR CONTEXT]: {error_context}
        [RETRY COUNT]: {state.retry_count}/{state.max_retries}
        """

        summarized_content = state.summary or "Analysis attempted but encountered technical challenges."
        summarized_context = AIMessage(content=f"Summary of attempts: {summarized_content}")
        
        request_messages = [
            summarized_context,
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_prompt)
        ]
        
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = json_llm.invoke(request_messages)
        response_data = json.loads(response.content)
        
        # Create response object with empty results since circuit breaker was triggered
        response_obj = FinalPresentation(**response_data, results=[])
        
        result_message = AIMessage(content=response_obj.model_dump_json())
        
        return {
            "messages": [result_message],
            "summary": state.summary + f"\n\n[CIRCUIT BREAKER]: Analysis terminated after {state.retry_count} retry attempts",
            "circuit_breaker_triggered": True
        }

    async def _handle_no_results_response(self, state: SQLAssistantState):
        """Handle responses when no execution results are available"""
        original_question = state.input
        interpretation = state.interpretation.objective if state.interpretation else "analyzing your question"
        
        system_prompt = """
        You are a Data Scientist who analyzed a question but couldn't retrieve data results.
        Provide a helpful response explaining what was attempted and suggest alternatives.
        
        **JSON Output Format**:
        {
            "ready_to_present": true,
            "interpretation_correct": true,
            "message": "<Helpful explanation in markdown>",
            "next_questions": [
                "Would you like to explore the available tables first?",
                "Could you provide more specific criteria?",
                "Are there particular metrics you're most interested in?"
            ]
        }
        """

        context_prompt = f"""
        [ORIGINAL QUESTION]: {original_question}
        [INTERPRETATION]: {interpretation}
        [EXPLORATION FINDINGS]: {state.exploration_findings or 'Database structure analyzed'}
        """

        request_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_prompt)
        ]
        
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = json_llm.invoke(request_messages)
        response_data = json.loads(response.content)
        
        response_obj = FinalPresentation(**response_data, results=[])
        result_message = AIMessage(content=response_obj.model_dump_json())
        
        return {
            "messages": [result_message],
            "summary": state.summary + "\n\n[NO RESULTS]: Analysis completed but no data results available"
        }

    async def _handle_minimal_response(self, state: SQLAssistantState, row_dicts: list):
        """Handle responses with results but no observation report"""
        original_question = state.input
        interpretation = state.interpretation.objective if state.interpretation else "analyzing your question"
        
        system_prompt = """
        You are a Data Scientist presenting query results to a user.
        You have the data but limited analysis context.
        
        **JSON Output Format**:
        {
            "ready_to_present": true,
            "interpretation_correct": true,
            "message": "<Data presentation in markdown>",
            "next_questions": [
                "What patterns do you see in this data?",
                "Would you like to filter or group this data differently?",
                "Are there specific insights you're looking for?"
            ]
        }
        """

        context_prompt = f"""
        [ORIGINAL QUESTION]: {original_question}
        [INTERPRETATION]: {interpretation}
        [RESULTS COUNT]: {len(row_dicts)}
        [SAMPLE DATA]: {json.dumps(row_dicts[:3], indent=2) if row_dicts else 'No data'}
        """

        request_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_prompt)
        ]
        
        json_llm = self.handler.model.bind(response_format={"type": "json_object"})
        response = json_llm.invoke(request_messages)
        response_data = json.loads(response.content)
        
        response_obj = FinalPresentation(**response_data, results=row_dicts)
        result_message = AIMessage(content=response_obj.model_dump_json())
        
        return {
            "messages": [result_message],
            "summary": state.summary + f"\n\n[MINIMAL ANALYSIS]: Presented {len(row_dicts)} results with basic context"
        }

    async def _handle_normal_response(self, state: SQLAssistantState, row_dicts: list, selected_tables: list, table_schemas_json: str):
        """Handle normal responses with full data and analysis"""
        observed_report = state.query_observation_report
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
        2. **CRITICAL**: Always generate a helpful markdown message regardless of whether objectives were met or not:
           - If all_objectives_met is True: Present the findings and insights clearly
           - If some_objectives_met is True: Present partial findings and explain what couldn't be determined
           - If no objectives were met: Explain why no relevant data was found and provide valuable context about what was discovered
        3. When no objectives are met, focus on:
           - What the query searched for and why it returned no results
           - What this tells us about the data or the question
           - Alternative approaches or refined questions that might yield results
           - Any insights gained from the exploration process
        4. If you are ready to present the data to the user then imagine you're presenting this data to a non-technical
           person. Make sure that the data is easy to understand and the insights are clear.
        5. Do not mention anything about technical items like "objectives_met", "analysis report", etc. 
        6. In case if you are referring to any datapoint, make sure to use the entity name as well. Do not use names
           like Category A, instead say <Category [Category ID]>.
        7. Generate 3-5 follow-up questions that the user might want to ask to go deeper into this analysis. These should
           be natural questions that build on the current findings and help the user explore related aspects of their data.
           
        **JSON Output Format**
        {
            "ready_to_present": true,
            "interpretation_correct": true,
            "message": "<ALWAYS provide a helpful markdown message explaining the findings, insights, or why no data was found>",
            "next_questions": [
                "What trends do you see in [specific metric] over the past year?",
                "How does [finding] compare across different [categories/segments]?",
                "What factors might be contributing to [observed pattern]?"
            ]
        }
        """

        context_prompt = f"""
        [ORIGINAL QUESTION]: {original_question}
        
        [INTERPRETATION]:

        {interpretation.objective}
        
        [Analysis Report]: {observed_report.model_dump_json()}
        
        **Database Info Availability**:
        
        [SELECTED TABLES]: {selected_tables}
        
        [TABLE SCHEMAS]: {table_schemas_json}
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

        result_message = AIMessage(content=response.model_dump_json())
        
        return {
            "messages": [result_message],
            "summary": msg_summary
        }
