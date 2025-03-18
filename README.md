# Doorbeen
Doorbeen is an intelligent SQL assistant that connects Large Language Models (LLMs) with databases, allowing users to interact with their data using natural language. Ask questions about your data in plain English, and Doorbeen translates them into SQL queries, executes them, and presents the results in a human-readable format.

## Features
- **Natural Language Interface**: Ask questions about your data in plain English without writing SQL
- **Multi-Database Support**: Connect to PostgreSQL, MySQL, Oracle, SQLite, BigQuery, and MongoDB
- **Intelligent Query Generation**: Translates questions into optimized SQL queries
- **Error Handling**: Automatically detects and fixes SQL errors
- **Result Analysis**: Analyzes query results and presents insights in an understandable format
- **Data Visualization**: Generates visualizations based on query results
- **Streaming Responses**: View results as they are generated
- **Follow-up Questions**: Ask follow-up questions that maintain context from previous queries




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

## Supported Databases

- PostgreSQL
- MySQL  
- Oracle
- SQLite
- BigQuery
- MongoDB

## Usage Example

```python
from doorbeen import SQLAssistant
from core.models.model import ModelInstance

# Configure database connection
db_credentials = {
    "host": "localhost",
    "port": 5432,
    "username": "user",
    "password": "password",
    "database": "mydb"
}

# Initialize SQL assistant
assistant = SQLAssistant(
    client=CommonSQLClient(credentials=db_credentials),
    db_type="postgresql",
    model=ModelInstance(name="gpt-4", api_key="your-api-key")
)

# Ask a question in natural language
response = assistant.ask_assistant(
    question="What were our top 5 customers by revenue last month?"
)

# Access the results
print(f"SQL Query: {response.query}")
print(f"Results: {response.result}")
```


                    ┌───────────────┐
                    │ Input/Question│
                    └───────┬───────┘
                            │
                    ┌───────▼────────┐
                    │Input Assessment│
                    └───────┬────────┘
                            │
               ┌────────────┴────────────┐
               │                         │
      ┌────────▼─────────┐     ┌─────────▼────────┐
      │Follow-up Question│     │    New Question  │
      └────────┬─────────┘     └────────┬─────────┘
               │                        │
    ┌──────────▼─────────┐     ┌────────▼───────┐
    │Answer if Possible  │     │    QA Grade    │
    │   Otherwise        │     └───────┬────────┘
    │   Process Further  │             │
    └──────────┬─────────┘     ┌───────▼────────┐
               │               │  Input Enrich  │
               │               │  (if needed)   │
               │               └───────┬────────┘
               │                       │
               │               ┌───────▼────────┐
               │               │    Interpret   │
               │               └───────┬────────┘
               │                       │
               │               ┌───────▼────────┐
               └──────────────►│ Generate Query │
                               └───────┬────────┘
                                       │
                               ┌───────▼─────────┐
                               │Execute SQL Query│
                               └───────┬─────────┘
                                       │
                       ┌───────────────┴───────────────┐
                       │                               │
              ┌────────▼─────────┐          ┌──────────▼────────┐
              │Process Results   │          │ Execution Failure │
              └────────┬─────────┘          └──────────┬────────┘
                       │                               │
              ┌────────▼──────────┐                     │
              │All Objectives Met?│                    │
              └─────────┬─────────┘                    │
                        │                              │
           ┌────────────┴─────────────────┐            │
           │                              │            │
    ┌──────▼──────┐              ┌────────▼───────┐    │
    │Final Answer │              │Regenerate Query│◄───┘
    └─────────────┘              └────────────────┘

## Development

Doorbeen uses a modular architecture that makes it easy to add new capabilities:

- Add new database support by implementing connector classes
- Create new analysis nodes for specialized data processing
- Extend visualization capabilities for different data types
- Add new LLM models for improved performance

## API Documentation

You can access the complete API documentation by navigating to the `/docs` route after starting the application. This interactive documentation provides details on all available endpoints, request parameters, and response formats.

## Docker Setup

### Building and Running with Docker

1. **Build the Docker image**:
   ```bash
   docker build -t doorbeen .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 -e DATABASE_URL=your_connection_string -e API_KEY=your_llm_api_key doorbeen
   ```

3. **Using Docker Compose**:
   
   Create a `docker-compose.yml` file:
   ```yaml
   version: '3'
   services:
     doorbeen:
       build: .
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=your_connection_string
         - API_KEY=your_llm_api_key
   ```
   
   Then run:
   ```bash
   docker-compose up
   ```

After starting the container, you can access the application at `http://localhost:8000` and the API documentation at `http://localhost:8000/docs`.

## License

Doorbeen is licensed under the MIT License, a short and simple permissive license with conditions only requiring preservation of copyright and license notices. Licensed works, modifications, and larger works may be distributed under different terms and without source code.
