import json
import uuid
import re
import logging
from typing import Optional, Dict, List, Any, ClassVar

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.assistants.prompts.inputs.enrich import enrich_input
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.enrich import EnrichedOutput
from doorbeen.core.types.ts_model import TSModel


class QuestionPatternMatcher(TSModel):
    """
    Utility class that matches user questions to common analytical patterns and suggests
    appropriate enrichment strategies. Used by existing enrichment logic.
    """
    
    PATTERNS: ClassVar[Dict[str, Dict[str, Any]]] = {
        "correlation": {
            "regex": r"correlation between (.*?) and (.*?)(?:\?|$)",
            "enrichment_strategy": "define_thresholds_and_temporal_relationship",
            "required_assumptions": ["threshold_definition", "temporal_scope"]
        },
        "trend": {
            "regex": r"(.*?) over time",
            "enrichment_strategy": "define_time_granularity_and_period",
            "required_assumptions": ["time_period", "aggregation_level"]
        },
        "comparison": {
            "regex": r"compare (.*?) between (.*?) and (.*?)",
            "enrichment_strategy": "define_comparison_criteria",
            "required_assumptions": ["grouping_criteria", "metric_definition"]
        },
        "performance": {
            "regex": r"(performance|how well|effectiveness)",
            "enrichment_strategy": "identify_performance_metrics",
            "required_assumptions": ["metric_definition", "benchmark_criteria"]
        },
        "high_low": {
            "regex": r"(high|low|highest|lowest|top|bottom)",
            "enrichment_strategy": "define_threshold_criteria",
            "required_assumptions": ["threshold_definition", "ranking_criteria"]
        }
    }
    
    def match_pattern(self, question: str) -> Optional[Dict[str, Any]]:
        """Match question against known patterns and return enrichment strategy"""
        logging.info(f"🔍 [PATTERN_MATCHER] Analyzing question: {question}")
        
        question_lower = question.lower()
        
        for pattern_name, pattern_info in self.PATTERNS.items():
            if re.search(pattern_info["regex"], question_lower, re.IGNORECASE):
                logging.info(f"✅ [PATTERN_MATCHER] Matched pattern: {pattern_name}")
                logging.info(f"   - Strategy: {pattern_info['enrichment_strategy']}")
                logging.info(f"   - Required assumptions: {pattern_info['required_assumptions']}")
                return {
                    "pattern_type": pattern_name,
                    "enrichment_strategy": pattern_info["enrichment_strategy"],
                    "required_assumptions": pattern_info["required_assumptions"]
                }
        
        logging.info("ℹ️ [PATTERN_MATCHER] No specific pattern matched - using general enrichment")
        return {
            "pattern_type": "general",
            "enrichment_strategy": "general_clarification",
            "required_assumptions": ["context_clarification", "scope_definition"]
        }


class DatasetAwareEnrichmentEngine(TSModel):
    """
    Enhanced enrichment engine that analyzes database schema to provide
    dataset-specific enrichment suggestions and assumptions.
    """
    
    def analyze_schema_for_enrichment(self, table_schemas, question: str) -> Dict[str, Any]:
        """Analyze database schema to provide context-aware enrichment"""
        logging.info("🔍 [ENRICHMENT_ENGINE] Starting schema analysis for enrichment")
        
        if not table_schemas or not table_schemas.tables:
            logging.warning("⚠️ [ENRICHMENT_ENGINE] No table schemas available")
            return {"temporal_columns": [], "numeric_metrics": [], "categorical_groupings": []}
        
        temporal_columns = []
        numeric_metrics = []
        categorical_groupings = []
        
        for table in table_schemas.tables:
            logging.info(f"🔍 [ENRICHMENT_ENGINE] Analyzing table: {table.name}")
            
            for column in table.columns:
                column_name_lower = column.name.lower()
                column_type_lower = column.type.lower()
                
                # Identify temporal columns
                if any(keyword in column_name_lower for keyword in ['time', 'date', 'timestamp', 'created', 'updated']):
                    temporal_columns.append(f"{table.name}.{column.name}")
                
                # Identify numeric metrics
                if any(keyword in column_type_lower for keyword in ['int', 'real', 'float', 'numeric', 'decimal']):
                    if not any(keyword in column_name_lower for keyword in ['id', 'uuid', 'key']):
                        numeric_metrics.append(f"{table.name}.{column.name}")
                
                # Identify categorical columns
                if 'varchar' in column_type_lower or 'text' in column_type_lower:
                    if any(keyword in column_name_lower for keyword in ['type', 'category', 'status', 'group', 'class']):
                        categorical_groupings.append(f"{table.name}.{column.name}")
        
        logging.info(f"🔍 [ENRICHMENT_ENGINE] Schema analysis complete:")
        logging.info(f"   - Temporal columns: {len(temporal_columns)}")
        logging.info(f"   - Numeric metrics: {len(numeric_metrics)}")
        logging.info(f"   - Categorical groupings: {len(categorical_groupings)}")
        
        return {
            "temporal_columns": temporal_columns,
            "numeric_metrics": numeric_metrics,
            "categorical_groupings": categorical_groupings
        }
    
    def generate_data_driven_assumptions(self, question: str, schema_analysis: Dict[str, Any], pattern_match: Dict[str, Any]) -> List[str]:
        """Generate assumptions based on actual data structure"""
        logging.info("🔍 [ENRICHMENT_ENGINE] Generating data-driven assumptions")
        
        assumptions = []
        
        # Pattern-specific assumptions
        if pattern_match["pattern_type"] == "correlation":
            if schema_analysis["numeric_metrics"]:
                assumptions.append(f"Correlation will be calculated using available numeric metrics: {', '.join(schema_analysis['numeric_metrics'][:3])}")
            if schema_analysis["temporal_columns"]:
                assumptions.append(f"Time-based analysis will use temporal columns: {', '.join(schema_analysis['temporal_columns'][:2])}")
        
        elif pattern_match["pattern_type"] == "trend":
            if schema_analysis["temporal_columns"]:
                assumptions.append(f"Trend analysis will use time columns: {', '.join(schema_analysis['temporal_columns'][:2])}")
            assumptions.append("Default time granularity: daily aggregation unless specified otherwise")
        
        elif pattern_match["pattern_type"] == "high_low":
            if schema_analysis["numeric_metrics"]:
                assumptions.append(f"Ranking will be based on numeric metrics: {', '.join(schema_analysis['numeric_metrics'][:3])}")
            assumptions.append("Default threshold: top/bottom 10% unless specified otherwise")
        
        # General assumptions
        if schema_analysis["categorical_groupings"]:
            assumptions.append(f"Grouping options available: {', '.join(schema_analysis['categorical_groupings'][:3])}")
        
        logging.info(f"🔍 [ENRICHMENT_ENGINE] Generated {len(assumptions)} data-driven assumptions")
        return assumptions


class EnrichInputNode(TSModel):
    handler: ModelHandler

    async def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        logging.info("🚀 [ENRICH_NODE] Starting enrichment process")
        logging.info(f"🔍 [ENRICH_NODE] Input question: {state.input}")
        logging.info(f"🔍 [ENRICH_NODE] Should enrich flag: {getattr(state, 'should_enrich', 'not set')}")
        
        try:
            configuration = config.get("configurable", {})
            connection: CommonSQLClient = configuration.get("connection", None)
            
            # Log connection status
            if connection:
                logging.info("✅ [ENRICH_NODE] Database connection available")
            else:
                logging.warning("⚠️ [ENRICH_NODE] No database connection found")
            
            # Use schema from state if available
            if state.table_schemas:
                logging.info("✅ [ENRICH_NODE] Using cached table schemas from state")
                table_schemas = state.table_schemas
            else:
                logging.info("🔍 [ENRICH_NODE] Loading table schemas from database")
                table_schemas = connection.get_schema()
                logging.info(f"✅ [ENRICH_NODE] Loaded {len(table_schemas.tables)} tables")
            
            # Initialize enrichment components
            logging.info("🔍 [ENRICH_NODE] Initializing enrichment components")
            pattern_matcher = QuestionPatternMatcher()
            enrichment_engine = DatasetAwareEnrichmentEngine()
            
            # Pattern matching
            logging.info("🔍 [ENRICH_NODE] Starting pattern matching")
            pattern_match = pattern_matcher.match_pattern(state.input)
            
            # Schema analysis
            logging.info("🔍 [ENRICH_NODE] Starting schema analysis")
            schema_analysis = enrichment_engine.analyze_schema_for_enrichment(table_schemas, state.input)
            
            # Generate assumptions
            logging.info("🔍 [ENRICH_NODE] Generating data-driven assumptions")
            data_driven_assumptions = enrichment_engine.generate_data_driven_assumptions(
                state.input, schema_analysis, pattern_match
            )
            
            # Call the enrichment function
            logging.info("🔍 [ENRICH_NODE] Invoking LLM for question enrichment")
            
            # Format schema information for the prompt
            schema_info = ""
            for table in table_schemas.tables:
                schema_info += f"Table: {table.name}\n"
                for column in table.columns:
                    schema_info += f"  - {column.name}: {column.type}\n"
                schema_info += "\n"
            
            # Get the enrichment prompt
            enrichment_prompt = enrich_input(schema_info)
            
            # Create the full prompt with context
            full_prompt = f"""
            {enrichment_prompt}
            
            **Current Context**:
            - User Question: {state.input}
            - Pattern Detected: {pattern_match['pattern_type']}
            - Enrichment Strategy: {pattern_match['enrichment_strategy']}
            - Data-Driven Assumptions: {', '.join(data_driven_assumptions)}
            - Available Schema: {schema_info}
            
            Please enrich the user's question following the guidelines above.
            """
            
            # Create messages for the LLM
            messages = [
                SystemMessage(content=full_prompt)
            ]
            
            # Use JSON mode for structured output
            json_llm = self.handler.model.bind(response_format={"type": "json_object"})
            response = await json_llm.ainvoke(messages)
            
            # Parse the response
            enriched_output = json.loads(response.content)
            
            logging.info("✅ [ENRICH_NODE] LLM enrichment completed")
            logging.info(f"🔍 [ENRICH_NODE] Enriched question: {enriched_output.get('improved_input', 'not provided')}")
            
            # Extract enrichment results
            enriched_question = enriched_output.get("improved_input", state.input)
            assumptions_made = enriched_output.get("assumptions", {})
            alternative_questions = enriched_output.get("variations", [])
            
            logging.info(f"🔍 [ENRICH_NODE] Enrichment results:")
            logging.info(f"   - Original: {state.input}")
            logging.info(f"   - Enriched: {enriched_question}")
            logging.info(f"   - Assumptions: {len(assumptions_made)}")
            logging.info(f"   - Alternatives: {len(alternative_questions)}")
            
            # Create result message
            result_message = AIMessage(content=json.dumps(enriched_output))
            
            # Update summary
            summary = state.summary + f"\n\n[ENRICHMENT]: Question enhanced from '{state.input}' to '{enriched_question}'"
            summary += f"\nAssumptions made: {len(assumptions_made)}"
            summary += f"\nAlternative questions generated: {len(alternative_questions)}"
            
            logging.info("✅ [ENRICH_NODE] Enrichment process completed successfully")
            
            return {
                "messages": [result_message],
                "input": enriched_question,  # Update the input with enriched version
                "enriched_question": enriched_question,
                "assumptions_made": assumptions_made,
                "alternative_questions": alternative_questions,
                "enrichment_strategy": pattern_match["enrichment_strategy"],
                "relevance_assessment": f"Question enriched using {pattern_match['pattern_type']} pattern",
                "table_schemas": table_schemas,
                "summary": summary
            }
            
        except Exception as e:
            logging.error(f"❌ [ENRICH_NODE] Enrichment failed with error: {str(e)}")
            logging.error(f"❌ [ENRICH_NODE] Error type: {type(e).__name__}")
            logging.error(f"❌ [ENRICH_NODE] This may cause downstream failures")
            
            # Return original state with error information
            return {
                "messages": [AIMessage(content=f"Enrichment failed: {str(e)}")],
                "input": state.input,  # Keep original input
                "enrichment_error": str(e),
                "summary": state.summary + f"\n\n[ENRICHMENT ERROR]: {str(e)}"
            }
