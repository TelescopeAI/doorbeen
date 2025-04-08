### Key Components

- **SQLAgentGraphBuilder**: Builds the workflow graph for SQL query processing
- **QueryGenerator**: Generates SQL queries based on user questions
- **QueryExecutor**: Executes SQL queries against the connected database
- **QueryResultsAnalysis**: Analyzes results and extracts insights
- **FinalizeAnswerNode**: Creates final, human-readable answers

## How It Works

1. **Question Analysis**: When you ask a question, Doorbeen analyzes it to understand your intent and required data
2. **Schema Understanding**: Examines your database schema to identify relevant tables and columns
3. **Query Generation**: Translates your question into an optimized SQL query
4. **Execution**: Runs the query against your database
5. **Result Analysis**: Analyzes the query results for insights
6. **Refinement**: If needed, refines the query to better match your intent
7. **Presentation**: Formats the results and insights in a clear, human-readable way