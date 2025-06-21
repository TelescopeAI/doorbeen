import json
import uuid
import re
from enum import Enum
from logging import info
from typing import Any, Optional, List, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from doorbeen.core.assistants.analysis.sql.state import SQLAssistantState
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.models.provider import ModelHandler
from doorbeen.core.types.ts_model import TSModel
from doorbeen.core.types.sql_schema import DatabaseSchema, TableSchema


class DeterminedQuestionTypes(Enum):
    NEW = "new"
    FOLLOWUP = "followup"


class InitAssistant(TSModel):
    handler: ModelHandler = None
    qn: Optional[str] = None

    async def _extract_table_hints_from_query(self, query: str) -> List[str]:
        """Extract potential table names from user query using simple heuristics"""
        
        # Simple patterns to detect table names
        # Look for common SQL-like references
        table_patterns = [
            r'\bfrom\s+(\w+)',
            r'\bjoin\s+(\w+)', 
            r'\btable\s+(\w+)',
            r'\b(\w+)\s+table',
        ]
        
        potential_tables = []
        query_lower = query.lower()
        
        for pattern in table_patterns:
            matches = re.findall(pattern, query_lower)
            potential_tables.extend(matches)
        
        # Remove duplicates and common words
        common_words = {'user', 'data', 'info', 'table', 'from', 'where', 'select'}
        return [t for t in set(potential_tables) if t not in common_words]

    async def _load_relevant_schema(self, query: str, connection: CommonSQLClient) -> DatabaseSchema:
        """Load schema using dataset-agnostic domain detection approach"""
        
        # Get ALL available tables first  
        all_tables = connection.get_table_names(schema_name=connection.credentials.database)
        full_schema = connection.get_schema()
        
        print(f"DEBUG: All available tables: {all_tables}")
        
        # 🎯 DATASET-AGNOSTIC DOMAIN DETECTION
        # Use LLM to identify relevant tables based on question semantics
        priority_tables = await self._detect_relevant_tables_with_llm(query, all_tables)
        
        print(f"DEBUG: LLM-detected priority tables: {priority_tables}")
        
        # Build relevant schema with priority tables first, then others
        relevant_tables = []
        used_table_names = set()
        
        # Add priority tables first
        for table_name in priority_tables:
            for table_obj in full_schema.tables:
                if table_obj.name.lower() == table_name.lower() and table_name not in used_table_names:
                    relevant_tables.append(table_obj)
                    used_table_names.add(table_name)
                    break
        
        # Add other tables up to reasonable limit (10 total max)
        remaining_slots = 10 - len(relevant_tables)
        for table_obj in full_schema.tables:
            if len(relevant_tables) >= 10:
                break
            if table_obj.name not in used_table_names:
                relevant_tables.append(table_obj)
                used_table_names.add(table_obj.name)
                remaining_slots -= 1
        
        print(f"DEBUG: Final selected tables: {[t.name for t in relevant_tables]}")
        
        # Always return at least some tables
        if not relevant_tables:
            relevant_tables = full_schema.tables[:5]  # Emergency fallback
            
        return DatabaseSchema(tables=relevant_tables)
    
    async def _detect_relevant_tables_with_llm(self, query: str, available_tables: List[str]) -> List[str]:
        """Use LLM to detect domain-relevant tables - completely dataset agnostic"""
        
        domain_prompt = f"""
You are a database expert who identifies relevant tables for user questions.

USER QUESTION: {query}
AVAILABLE TABLES: {', '.join(available_tables)}

TASK: Identify the most relevant tables for this question using semantic matching.

INSTRUCTIONS:
1. Look for DIRECT semantic matches between question keywords and table names
2. Consider domain relationships (e.g., "sleep" question → "sleep" table if available)  
3. Prioritize tables with names that directly relate to the question domain
4. Consider related tables that might provide context
5. Return table names in priority order (most relevant first)

CRITICAL: Base decisions ONLY on table names and question content. Don't assume data structure.

Return only a comma-separated list of table names in priority order.
"""

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            messages = [
                SystemMessage(content=domain_prompt),
                HumanMessage(content=f"Question: {query}")
            ]
            
            response = await self.handler.model.ainvoke(messages)
            
            # Parse LLM response to extract table names
            response_text = response.content.strip()
            
            # Extract table names (handle various response formats)
            table_names = []
            for line in response_text.split('\n'):
                # Look for comma-separated lists
                if ',' in line:
                    potential_tables = [t.strip() for t in line.split(',')]
                    # Validate against available tables
                    for table in potential_tables:
                        table_clean = table.strip().strip('"').strip("'")
                        if table_clean in available_tables and table_clean not in table_names:
                            table_names.append(table_clean)
                # Look for individual table names
                else:
                    table_clean = line.strip().strip('"').strip("'")
                    if table_clean in available_tables and table_clean not in table_names:
                        table_names.append(table_clean)
            
            # If LLM detection didn't work, fall back to keyword matching
            if not table_names:
                table_names = self._fallback_keyword_matching(query, available_tables)
            
            return table_names[:8]  # Return top 8 tables max
            
        except Exception as e:
            print(f"LLM table detection failed: {e}")
            # Fallback to keyword matching
            return self._fallback_keyword_matching(query, available_tables)
    
    def _fallback_keyword_matching(self, query: str, available_tables: List[str]) -> List[str]:
        """Fallback: simple keyword matching when LLM fails"""
        
        query_words = set(query.lower().split())
        table_scores = []
        
        for table in available_tables:
            table_words = set(table.lower().replace('_', ' ').split())
            # Simple overlap scoring
            overlap = len(query_words.intersection(table_words))
            # Boost score for exact keyword matches
            for word in query_words:
                if word in table.lower():
                    overlap += 2
            table_scores.append((table, overlap))
        
        # Sort by score and return top tables
        table_scores.sort(key=lambda x: x[1], reverse=True)
        return [table for table, score in table_scores if score > 0][:5]

    async def _analyze_conversation_context(self, current_question: str, conversation_context: str) -> dict:
        """Analyze conversation context to provide intelligent recall references"""
        
        if not conversation_context or not conversation_context.strip():
            return {
                "has_context": False,
                "question_type": "new",
                "recall_reference": None,
                "context_analysis": "This appears to be a new question with no previous conversation context."
            }
        
        # Use LLM to analyze the relationship between current question and context
        analysis_prompt = """
You are analyzing whether a current question has meaningful connections to previous conversation context.

INSTRUCTIONS:
1. Determine if the current question genuinely relates to or builds upon the previous context
2. If there IS a meaningful connection, provide a specific recall reference explaining what from the previous context is relevant
3. If there is NO meaningful connection, classify it as a new question
4. Be conservative - only mark as related if there's a clear, specific connection

EVALUATION CRITERIA FOR "RELATED":
- References specific data, metrics, or findings from previous context
- Asks for clarification, expansion, or drill-down on previous results  
- Uses pronouns or references that only make sense with previous context
- Builds directly upon previous analysis

EVALUATION CRITERIA FOR "NEW":
- Completely different topic or domain
- No reference to previous findings or data
- Could be understood without any previous context
- Generic questions that happen to follow other questions

OUTPUT FORMAT:
{
    "has_meaningful_connection": true/false,
    "question_type": "related" or "new", 
    "recall_reference": "Specific reference to what from previous context is relevant, or null if not related",
    "context_analysis": "Brief explanation of your reasoning",
    "confidence_level": "high/medium/low"
}
"""

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            context_prompt = f"""
PREVIOUS CONVERSATION CONTEXT:
{conversation_context}

CURRENT QUESTION:
{current_question}

Analyze whether the current question has a meaningful connection to the previous context.
"""

            messages = [
                SystemMessage(content=analysis_prompt),
                HumanMessage(content=context_prompt)
            ]
            
            json_llm = self.handler.model.bind(response_format={"type": "json_object"})
            response = await json_llm.ainvoke(messages)
            analysis = json.loads(response.content)
            
            # Validate the response structure
            required_fields = ["has_meaningful_connection", "question_type", "recall_reference", "context_analysis"]
            if not all(field in analysis for field in required_fields):
                raise ValueError("Invalid analysis response structure")
            
            return {
                "has_context": True,
                "question_type": analysis["question_type"],
                "recall_reference": analysis["recall_reference"] if analysis["has_meaningful_connection"] else None,
                "context_analysis": analysis["context_analysis"],
                "confidence_level": analysis.get("confidence_level", "medium"),
                "has_meaningful_connection": analysis["has_meaningful_connection"]
            }
            
        except Exception as e:
            print(f"Context analysis failed: {e}")
            # Conservative fallback - treat as new question if analysis fails
            return {
                "has_context": True,
                "question_type": "new",
                "recall_reference": None,
                "context_analysis": f"Unable to analyze context relationship. Treating as new question. Error: {str(e)}",
                "confidence_level": "low",
                "has_meaningful_connection": False
            }

    def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        configuration = config.get("configurable", {})
        messages_length = len(state.messages)
        connection: CommonSQLClient = configuration.get("connection", None)
        print("Starting SQL Analysis. Entry Node is initialized.")
        print(f"Connection: {connection}")
        print(f"Thread ID: {configuration.get('thread_id')}")
        
        # Extract conversation context from previous messages
        conversation_context = ""
        if len(state.messages) > 1:
            # Build context from previous messages (excluding the current question)
            context_messages = []
            for msg in state.messages[:-1]:  # All except current
                if hasattr(msg, 'content'):
                    # Try to extract meaningful content, skip system messages and technical responses
                    content = msg.content
                    if isinstance(content, str) and len(content.strip()) > 0:
                        # Skip overly technical JSON responses, keep user questions and assistant summaries
                        if not (content.strip().startswith('{') and content.strip().endswith('}')):
                            context_messages.append(f"{msg.__class__.__name__}: {content}")
                        elif "message" in content.lower() or "summary" in content.lower():
                            # Include JSON responses that contain user-facing messages
                            context_messages.append(f"{msg.__class__.__name__}: {content}")
            
            conversation_context = "\n".join(context_messages[-3:])  # Last 3 meaningful messages

        # Analyze conversation context for intelligent recall references
        import asyncio
        context_analysis = asyncio.run(self._analyze_conversation_context(self.qn or "", conversation_context))
        
        # Smart schema loading
        try:
            # Try smart loading first
            relevant_schema = asyncio.run(self._load_relevant_schema(self.qn or "", connection))
            selected_tables = [table.name for table in relevant_schema.tables]
            print(f"Smart schema loading: {len(relevant_schema.tables)} tables loaded using smart_selective strategy")
            print(f"Selected tables: {selected_tables}")
        except Exception as e:
            # Fallback to original loading if smart loading fails
            print(f"Smart schema loading failed, falling back to full loading: {e}")
            selected_tables = connection.get_table_names(schema_name=connection.credentials.database)
            relevant_schema = connection.get_schema()

        # Build enhanced summary with context analysis
        state.request_count += 1
        summary = "" if state.summary is None else state.summary
        summary += "\n\n------------------------- [New Message Starts Here] -------------------------\n"
        summary += f"Message Order: {state.request_count}\n"
        summary += f"Question Type: {context_analysis['question_type']}\n"
        
        if context_analysis['recall_reference']:
            summary += f"Recall Reference: {context_analysis['recall_reference']}\n"
        
        if context_analysis['context_analysis']:
            summary += f"Context Analysis: {context_analysis['context_analysis']}\n"
        
        # Prepare enhanced output with context analysis
        determined_type = {
            "question_type": context_analysis['question_type'],
            "has_context": context_analysis['has_context'],
            "recall_reference": context_analysis['recall_reference'],
            "context_analysis": context_analysis['context_analysis'],
            "confidence_level": context_analysis.get('confidence_level', 'medium'),
            "has_meaningful_connection": context_analysis.get('has_meaningful_connection', False),
            "database_context": f"Analyzed {len(selected_tables)} relevant tables from database"
        }
        
        output = {
            "messages": [
                AIMessage(
                    content=json.dumps(determined_type),
                    name="init_assistant"
                )
            ],
            "request_count": state.request_count,
            "input": self.qn,
            "conversation_context": conversation_context,
            "context_length": len(conversation_context),
            "selected_tables": selected_tables,
            "table_schemas": relevant_schema,  # Now returns proper DatabaseSchema
            "summary": summary
        }

        print(f"DEBUG: output table_schemas type: {type(output['table_schemas'])}")
        return output


class DetermineInputObjectives(TSModel):
    llm: Optional[Any] = None

    def __call__(self, state: SQLAssistantState, config: RunnableConfig):
        return state
