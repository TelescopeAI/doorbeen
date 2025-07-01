import json
import logging

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.prompts.inputs.grader import grade_question
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel


class InputGradingNode(TSModel):
    handler: ModelHandler = None

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        logging.info("🔍 [QA_GRADE_NODE] Starting QA grading process")
        logging.info(f"🔍 [QA_GRADE_NODE] Input question: {state.input}")
        
        configuration = config.get("configurable", {})
        connection: CommonSQLClient = configuration.get("connection", None)
        
        # Log database connection status
        if connection:
            logging.info("🔍 [QA_GRADE_NODE] Database connection available")
        else:
            logging.warning("⚠️ [QA_GRADE_NODE] No database connection found")
        
        # Use schema from context if available, otherwise load from connection
        if state.table_schemas:
            logging.info("🔍 [QA_GRADE_NODE] Using cached table schemas from context")
            table_schemas = state.table_schemas
        else:
            logging.info("🔍 [QA_GRADE_NODE] Loading table schemas from database")
            table_schemas = connection.get_schema()
            logging.info(f"🔍 [QA_GRADE_NODE] Loaded {len(table_schemas.tables)} tables")

        # Log the grading process
        logging.info("🔍 [QA_GRADE_NODE] Invoking LLM for question grading")
        response = await grade_question(
            question=state.input,
            table_schemas=table_schemas,
            handler=self.handler
        )
        
        # Log the grading response
        logging.info("🔍 [QA_GRADE_NODE] LLM grading completed")
        logging.info(f"🔍 [QA_GRADE_NODE] Grading response: {json.dumps(response, indent=2)}")
        
        # Extract key metrics for logging
        relevance_score = response.get('relevance', {}).get('score', 'unknown')
        should_enrich = response.get('should_enrich', False)
        overall_score = response.get('overall', {}).get('score', 'unknown')
        
        logging.info(f"🔍 [QA_GRADE_NODE] Key metrics:")
        logging.info(f"   - Relevance score: {relevance_score}")
        logging.info(f"   - Should enrich: {should_enrich}")
        logging.info(f"   - Overall score: {overall_score}")
        
        # Determine routing decision
        if relevance_score != 'unknown' and relevance_score > 6:
            logging.warning(f"⚠️ [QA_GRADE_NODE] Question deemed irrelevant (score: {relevance_score}) - will trigger circuit breaker")
        elif should_enrich:
            logging.info("✅ [QA_GRADE_NODE] Question will be routed to enrichment")
        else:
            logging.info("✅ [QA_GRADE_NODE] Question will proceed without enrichment")

        result_message = AIMessage(content=json.dumps(response))
        
        logging.info("🔍 [QA_GRADE_NODE] QA grading node completed successfully")
        
        return {
            "messages": [result_message],
            "grade": response,
            "should_enrich": should_enrich,
            "table_schemas": table_schemas,
            "summary": state.summary + f"\n\n[QA GRADING]: Question evaluated - Relevance: {relevance_score}, Should enrich: {should_enrich}"
        }

