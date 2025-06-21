"""
Query Validation Utilities

This module provides utilities for validating SQL queries across different
database types. It includes syntax validation, semantic validation, and
performance analysis capabilities.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from langchain_community.utilities import SQLDatabase
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from .types import QueryValidationResult


class ValidationLevel(Enum):
    """Validation levels for query checking"""
    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
    PERFORMANCE = "performance"


class DatabaseDialect(Enum):
    """Supported database dialects for validation"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"


class QueryValidator:
    """Main query validation class"""
    
    def __init__(self, database_type: str, connection: Optional[CommonSQLClient] = None):
        self.database_type = database_type.lower()
        self.connection = connection
        self.dialect = self._get_dialect()
    
    def _get_dialect(self) -> DatabaseDialect:
        """Get the database dialect enum"""
        dialect_map = {
            "sqlite": DatabaseDialect.SQLITE,
            "postgresql": DatabaseDialect.POSTGRESQL,
            "postgres": DatabaseDialect.POSTGRESQL,
            "mysql": DatabaseDialect.MYSQL,
            "oracle": DatabaseDialect.ORACLE,
            "bigquery": DatabaseDialect.BIGQUERY,
            "snowflake": DatabaseDialect.SNOWFLAKE
        }
        return dialect_map.get(self.database_type, DatabaseDialect.SQLITE)
    
    async def validate_query(
        self,
        query: str,
        table_schemas: Dict[str, Any],
        validation_level: ValidationLevel = ValidationLevel.BASIC
    ) -> QueryValidationResult:
        """
        Validate a SQL query at the specified validation level
        
        Args:
            query: SQL query to validate
            table_schemas: Available table schemas
            validation_level: Level of validation to perform
            
        Returns:
            QueryValidationResult with validation details
        """
        
        logging.info(f"🔍 [VALIDATOR] Validating query at {validation_level.value} level")
        
        result = QueryValidationResult(
            is_valid=True,
            syntax_valid=True,
            semantic_valid=True,
            database_type=self.database_type,
            validation_level=validation_level.value
        )
        
        try:
            # Step 1: Basic syntax validation
            syntax_issues = self._validate_syntax(query)
            if syntax_issues:
                result.syntax_valid = False
                result.syntax_errors.extend(syntax_issues)
                result.is_valid = False
            
            # Step 2: Semantic validation
            if validation_level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.PERFORMANCE]:
                semantic_issues = self._validate_semantics(query, table_schemas)
                if semantic_issues:
                    result.semantic_valid = False
                    result.semantic_errors.extend(semantic_issues)
                    result.is_valid = False
            
            # Step 3: Performance validation (if requested)
            if validation_level == ValidationLevel.PERFORMANCE:
                performance_warnings = self._validate_performance(query, table_schemas)
                result.warnings.extend(performance_warnings)
            
            # Step 4: Database-specific validation
            dialect_issues = self._validate_dialect_specific(query)
            if dialect_issues:
                result.syntax_errors.extend(dialect_issues)
                result.syntax_valid = False
                result.is_valid = False
            
            # Step 5: Generate fix suggestions if needed
            if not result.is_valid:
                result.suggested_fixes = self._generate_fix_suggestions(
                    query, result.syntax_errors + result.semantic_errors
                )
            
            logging.info(f"✅ [VALIDATOR] Validation complete (valid: {result.is_valid})")
            return result
            
        except Exception as e:
            logging.error(f"❌ [VALIDATOR] Validation failed: {e}")
            result.is_valid = False
            result.syntax_valid = False
            result.semantic_valid = False
            result.semantic_errors.append(f"Validation error: {str(e)}")
            return result
    
    def _validate_syntax(self, query: str) -> List[str]:
        """Validate basic SQL syntax"""
        issues = []
        
        query_clean = query.strip()
        if not query_clean:
            issues.append("Query is empty")
            return issues
        
        query_upper = query_clean.upper()
        
        # Check for basic SQL structure
        if not any(keyword in query_upper for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']):
            issues.append("Query must contain a valid SQL statement (SELECT, INSERT, UPDATE, DELETE, or WITH)")
        
        # Check for balanced parentheses
        if query_clean.count('(') != query_clean.count(')'):
            issues.append("Unbalanced parentheses in query")
        
        # Check for balanced quotes
        single_quotes = query_clean.count("'") - query_clean.count("\\'")
        double_quotes = query_clean.count('"') - query_clean.count('\\"')
        
        if single_quotes % 2 != 0:
            issues.append("Unbalanced single quotes in query")
        
        if double_quotes % 2 != 0:
            issues.append("Unbalanced double quotes in query")
        
        # Check for common syntax errors
        if 'SELECT' in query_upper and 'FROM' not in query_upper:
            # Allow for some exceptions like SELECT NOW(), SELECT 1, etc.
            if not any(func in query_upper for func in ['NOW()', 'CURRENT_TIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIME']):
                if not re.search(r'SELECT\s+\d+', query_upper):  # SELECT 1, SELECT 42, etc.
                    issues.append("SELECT statement missing FROM clause")
        
        # Check for semicolon at end (optional but good practice)
        if not query_clean.endswith(';'):
            # This is a warning, not an error
            pass
        
        return issues
    
    def _validate_semantics(self, query: str, table_schemas: Dict[str, Any]) -> List[str]:
        """Validate semantic correctness against table schemas"""
        issues = []
        
        if not table_schemas:
            # Can't do semantic validation without schemas
            return issues
        
        query_upper = query.upper()
        
        # Extract table names from query (simplified approach)
        table_names = self._extract_table_names(query)
        
        # Check if referenced tables exist
        available_tables = set()
        if 'tables' in table_schemas:
            available_tables = {table.get('name', '').lower() for table in table_schemas['tables']}
        
        for table_name in table_names:
            if table_name.lower() not in available_tables:
                issues.append(f"Table '{table_name}' not found in schema")
        
        # Additional semantic checks could be added here:
        # - Column existence validation
        # - Data type compatibility
        # - JOIN condition validation
        # - Aggregate function usage
        
        return issues
    
    def _validate_performance(self, query: str, table_schemas: Dict[str, Any]) -> List[str]:
        """Validate query for performance issues"""
        warnings = []
        
        query_upper = query.upper()
        
        # Check for common performance issues
        if 'SELECT *' in query_upper:
            warnings.append("Consider specifying column names instead of SELECT *")
        
        if 'WHERE' not in query_upper and 'SELECT' in query_upper:
            warnings.append("Query lacks WHERE clause - may return large result set")
        
        if query_upper.count('JOIN') > 5:
            warnings.append("Query has many JOINs - consider performance implications")
        
        if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper:
            warnings.append("ORDER BY without LIMIT may be inefficient for large datasets")
        
        if 'LIKE' in query_upper and '%' in query:
            # Check for leading wildcards
            like_patterns = re.findall(r"LIKE\s+'([^']*)'", query, re.IGNORECASE)
            for pattern in like_patterns:
                if pattern.startswith('%'):
                    warnings.append("LIKE pattern with leading wildcard may be slow")
        
        return warnings
    
    def _validate_dialect_specific(self, query: str) -> List[str]:
        """Validate database-specific syntax"""
        issues = []
        
        if self.dialect == DatabaseDialect.SQLITE:
            issues.extend(self._validate_sqlite_specific(query))
        elif self.dialect == DatabaseDialect.POSTGRESQL:
            issues.extend(self._validate_postgresql_specific(query))
        elif self.dialect == DatabaseDialect.MYSQL:
            issues.extend(self._validate_mysql_specific(query))
        elif self.dialect == DatabaseDialect.ORACLE:
            issues.extend(self._validate_oracle_specific(query))
        elif self.dialect == DatabaseDialect.BIGQUERY:
            issues.extend(self._validate_bigquery_specific(query))
        
        return issues
    
    def _validate_sqlite_specific(self, query: str) -> List[str]:
        """SQLite-specific validation"""
        issues = []
        query_upper = query.upper()
        
        # SQLite doesn't support RIGHT JOIN
        if 'RIGHT JOIN' in query_upper:
            issues.append("SQLite doesn't support RIGHT JOIN - use LEFT JOIN instead")
        
        # SQLite has limited date functions
        if 'DATE_FORMAT(' in query_upper:
            issues.append("SQLite doesn't support DATE_FORMAT() - use strftime() instead")
        
        return issues
    
    def _validate_postgresql_specific(self, query: str) -> List[str]:
        """PostgreSQL-specific validation"""
        issues = []
        query_upper = query.upper()
        
        # PostgreSQL uses different string concatenation
        if 'CONCAT(' not in query_upper and '||' in query:
            # This is actually correct for PostgreSQL, just noting
            pass
        
        return issues
    
    def _validate_mysql_specific(self, query: str) -> List[str]:
        """MySQL-specific validation"""
        issues = []
        query_upper = query.upper()
        
        # MySQL uses backticks for identifiers
        if '`' in query:
            # This is valid MySQL syntax
            pass
        
        return issues
    
    def _validate_oracle_specific(self, query: str) -> List[str]:
        """Oracle-specific validation"""
        issues = []
        query_upper = query.upper()
        
        # Oracle uses ROWNUM instead of LIMIT
        if 'LIMIT' in query_upper:
            issues.append("Oracle doesn't support LIMIT - use ROWNUM instead")
        
        return issues
    
    def _validate_bigquery_specific(self, query: str) -> List[str]:
        """BigQuery-specific validation"""
        issues = []
        query_upper = query.upper()
        
        # BigQuery requires table references to be fully qualified in some cases
        # This would require more sophisticated parsing to validate properly
        
        return issues
    
    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from SQL query (simplified approach)"""
        table_names = []
        
        # This is a simplified regex-based approach
        # A proper implementation would use a SQL parser
        
        # Find FROM clauses
        from_matches = re.finditer(r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', query, re.IGNORECASE)
        for match in from_matches:
            table_names.append(match.group(1))
        
        # Find JOIN clauses
        join_matches = re.finditer(r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)', query, re.IGNORECASE)
        for match in join_matches:
            table_names.append(match.group(1))
        
        return list(set(table_names))  # Remove duplicates
    
    def _generate_fix_suggestions(self, query: str, errors: List[str]) -> List[str]:
        """Generate fix suggestions based on validation errors"""
        suggestions = []
        
        for error in errors:
            if "unbalanced parentheses" in error.lower():
                suggestions.append("Check and balance all parentheses in the query")
            elif "unbalanced quotes" in error.lower():
                suggestions.append("Check and balance all quotes in the query")
            elif "missing from clause" in error.lower():
                suggestions.append("Add a FROM clause to specify the data source")
            elif "table" in error.lower() and "not found" in error.lower():
                suggestions.append("Verify table names exist in the database schema")
            elif "right join" in error.lower():
                suggestions.append("Replace RIGHT JOIN with LEFT JOIN and swap table order")
            elif "date_format" in error.lower():
                suggestions.append("Use strftime() instead of DATE_FORMAT() for SQLite")
            elif "limit" in error.lower() and "oracle" in error.lower():
                suggestions.append("Use ROWNUM instead of LIMIT for Oracle databases")
        
        # Add general suggestions
        if not suggestions:
            suggestions.append("Review query syntax for the target database type")
        
        return suggestions


class QueryComplexityAnalyzer:
    """Analyze query complexity for performance estimation"""
    
    @staticmethod
    def analyze_complexity(query: str, table_schemas: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query complexity and return metrics"""
        
        query_upper = query.upper()
        
        complexity_score = 0
        factors = []
        
        # Count JOINs
        join_count = query_upper.count('JOIN')
        if join_count > 0:
            complexity_score += join_count * 2
            factors.append(f"{join_count} JOIN operations")
        
        # Count subqueries
        subquery_count = query.count('(') - query.count(')')
        if subquery_count > 0:
            complexity_score += subquery_count * 3
            factors.append(f"{subquery_count} subqueries")
        
        # Check for aggregations
        aggregations = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP BY']
        agg_count = sum(1 for agg in aggregations if agg in query_upper)
        if agg_count > 0:
            complexity_score += agg_count
            factors.append(f"{agg_count} aggregation functions")
        
        # Check for window functions
        window_functions = ['ROW_NUMBER', 'RANK', 'DENSE_RANK', 'OVER']
        window_count = sum(1 for func in window_functions if func in query_upper)
        if window_count > 0:
            complexity_score += window_count * 2
            factors.append(f"{window_count} window functions")
        
        # Determine complexity level
        if complexity_score <= 2:
            complexity_level = "low"
        elif complexity_score <= 8:
            complexity_level = "medium"
        else:
            complexity_level = "high"
        
        return {
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "contributing_factors": factors,
            "estimated_performance": QueryComplexityAnalyzer._estimate_performance(complexity_level)
        }
    
    @staticmethod
    def _estimate_performance(complexity_level: str) -> str:
        """Estimate performance based on complexity level"""
        performance_map = {
            "low": "Fast execution expected",
            "medium": "Moderate execution time, monitor performance",
            "high": "Potentially slow, consider optimization"
        }
        return performance_map.get(complexity_level, "Unknown")


# Utility functions for external use

async def validate_query_quick(
    query: str,
    database_type: str,
    table_schemas: Dict[str, Any] = None
) -> bool:
    """Quick validation function that returns True/False"""
    validator = QueryValidator(database_type)
    result = await validator.validate_query(query, table_schemas or {})
    return result.is_valid


async def get_query_issues(
    query: str,
    database_type: str,
    table_schemas: Dict[str, Any] = None
) -> List[str]:
    """Get list of issues with a query"""
    validator = QueryValidator(database_type)
    result = await validator.validate_query(query, table_schemas or {})
    return result.syntax_errors + result.semantic_errors


def analyze_query_complexity(query: str, table_schemas: Dict[str, Any] = None) -> Dict[str, Any]:
    """Analyze query complexity and return metrics"""
    return QueryComplexityAnalyzer.analyze_complexity(query, table_schemas or {}) 