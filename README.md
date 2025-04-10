```
      _                   _                       
     | |                 | |                      
   __| | ___   ___  _ __ | |__   ___  ___ _ __   
  / _` |/ _ \ / _ \| '__|| '_ \ / _ \/ _ \ '_ \  
 | (_| | (_) | (_) | |   | |_) |  __/  __/ | | | 
  \__,_|\___/ \___/|_|   |_.__/ \___|\___|_| |_| 
                                                  
```

Doorbeen is an intelligent SQL assistant that connects Large Language Models (LLMs) with databases, allowing users to interact with their data using natural language. Ask questions about your data in plain English, and Doorbeen translates them into SQL queries, executes them, and presents the results in a human-readable format.

## Features
- **Natural Language Interface**: Ask questions about your data in plain English without writing SQL
- **Multi-Database Support**: Connect to PostgreSQL, MySQL, Oracle, SQLite, BigQuery.
- **Intelligent Query Generation**: Translates questions into optimized SQL queries
- **Error Handling**: Automatically detects and fixes SQL errors
- **Result Analysis**: Analyzes query results and presents insights in an understandable format
- **Data Visualization**: Generates visualizations based on query results
- **Streaming Responses**: View results as they are generated
- **Follow-up Questions**: Ask follow-up questions that maintain context from previous queries


## Supported Databases

- PostgreSQL
- MySQL  
- Oracle
- SQLite
- BigQuery

## Before you get started

### Clerk Authentication
Doorbeen uses Clerk for user authentication. You'll need to create a Clerk account and set up an application to obtain your API keys.
For Clerk authentication setup, please refer to the [official documentation](https://clerk.com/docs/quickstarts/setup-clerk).


### Environment Setup
The repository contains example environment files that you should use as templates:
1. Root directory: Copy `example.env` to `local.env` and update the values:
```bash
cp example.env local.env
```

2. Frontend playground: Copy `frontend/playground/example.env` to `frontend/playground/local.env` and update the values:
```bash
cp frontend/playground/example.env frontend/playground/local.env
```
Be sure to replace placeholder values with your actual credentials:
- Replace `sk_test_password` with your Clerk Backend API Key
- Replace `pk_test_<unique-id>` with your Clerk Publishable Key
- Replace `sk_test_<unique-id>` with your Clerk Secret Key
- Update other environment variables as needed



## Get Started

Doorbeen can be used either as a Python package in your application or deployed as a standalone service using Docker (which includes a Playground UI). Here's how to use it as a package:

### Python Usage

### Installation

```bash
pip install doorbeen
```

#### Prerequisites

- **Database for Assistant Memory**: Set `ASSISTANT_MEMORY_LOCATION_URI` to a valid Postgres Database URI. It's recommended to use a separate database from your application database. Alternatively, you can use a separate schema in your existing Postgres DB.

  You can spin up a Postgres DB using Docker by following [this guide](https://www.docker.com/blog/how-to-use-the-postgres-docker-official-image/).

- Doorbeen uses langchain's checkpointers for memory functionality. For more information, see the [LangGraph persistence documentation](https://langchain-ai.github.io/langgraph/concepts/persistence/#checkpointer-libraries).



```python
import asyncio
import json
from doorbeen.api.schemas.requests.assistants import AskLLMRequest, DBConnectionRequestParams, ModelMetaRequest
from doorbeen.core.chat.assistants import AssistantService
from doorbeen.core.types.databases import DatabaseTypes

db_credentials = {
                "host": "localhost",
                "port": 5432,
                "username": "user",
                "password": "password",
                "database": "mydb",
                "dialect": "postgresql",
            }
model = {"name": "gpt-4o", "api_key": "<your_api_key>"}


async def main():
    # Create a request object with database connection details
    request = AskLLMRequest(
        question="What is the trend of user signups over the last 6 months, broken down by region?",
        connection=DBConnectionRequestParams(
            db_type=DatabaseTypes.POSTGRESQL,
            credentials=db_credentials
        ),
        model=ModelMetaRequest(**model), stream=True)

    # Initialize the Assistant Service
    assistant_service = AssistantService()

    # Example 1: Non-streaming response
    results = await assistant_service.process_llm_request(request, stream=False)
    print("Results:")
    for result in results:
        print("Event:", {
            "type": result['type'],
            "name": result['name'],
            "data": result['data'],
            "timestamp": result['occurred_at']
        })
        # If you need to parse the data field (which appears to be a JSON string)
        try:
            data = json.loads(result['data'])
            print("Parsed data:", data)
        except json.JSONDecodeError:
            print("Raw data:", result['data'])

    # Example 2: Streaming response
    print("\nStreaming response:")
    async_generator = await assistant_service.process_llm_request(request, stream=True)

    async for chunk in async_generator:
        # In a real application, you would send these chunks to the client
        print(f"Received chunk: {chunk}")


# Run the async example
if __name__ == "__main__":
    asyncio.run(main())
```

For deploying as a standalone service with the Playground UI, refer to the Docker deployment instructions below.

### Reasoning Flow
![Workflow Diagram](./doorbeen/api/workflow.png)


## Development

Doorbeen uses a modular architecture that makes it easy to add new capabilities:

- Add new database support by implementing connector classes
- Create new analysis nodes for specialized data processing
- Extend visualization capabilities for different data types
- Add new LLM models for improved performance

### Using direnv for automatic environment loading
The repository provides `.envrc` files in both the root and `frontend/playground` directories. If you use `direnv`, these files will automatically load the environment variables from your `.env` files.
To use `direnv`:
1. Install `direnv` following the official installation instructions
2. Run `direnv allow` in both the root directory and the `frontend/playground` directory
3. `direnv` will automatically load your environment variables when you navigate to these directories

## API Documentation

You can access the complete API documentation by navigating to the [`/api/v1/docs`](https://services.doorbeen.dev/api/v1/docs) route after starting the application. This interactive documentation provides details on all available endpoints, request parameters, and response formats.

## Docker Setup

### Building and Running with Docker

#### Docker Compose:
Make sure to add your environment files with the necessary configuration.
Then run:
```bash
docker compose up
```
This command will create and start all the required services.
After starting the container, you can access the application backend at http://localhost:9001, frontend at http://localhost:3000 and the API documentation at http://localhost:9001/api/v1/docs.


## License

Doorbeen is licensed under the MIT License, a short and simple permissive license with conditions only requiring preservation of copyright and license notices. Licensed works, modifications, and larger works may be distributed under different terms and without source code.
