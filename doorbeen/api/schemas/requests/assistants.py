from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import Field

from doorbeen.core.types.databases import DatabaseTypes
from doorbeen.core.types.ts_model import TSModel


class DBConnectionRequestParams(TSModel):
    db_type: DatabaseTypes
    credentials: dict = Field(
        ..., 
        description="The credentials for the database connection",
        examples=[
            {
                "db_type": "mysql",
                "credentials": {
                    "host": "localhost",
                    "port": "3306",
                    "username": "root",
                    "password": "password",
                    "database": "sandbox",
                    "dialect": "mysql"
                }
            },
            {
                "db_type": "postgresql",
                "credentials": {
                    "host": "localhost",
                    "port": "5432",
                    "username": "postgres_user",
                    "password": "password",
                    "database": "sandbox",
                    "dialect": "postgresql"
                }
            },
            {
                "db_type": "bigquery",
                "credentials": {
                    "project_id": "my-project-id",
                    "dataset_id": "my_dataset",
                    "service_account_details": "{dict of service account details}"
                }
            },
        ]
    )


class ModelMetaRequest(TSModel):
    name: str = Field(..., description="The name of the language model")
    api_key: Optional[str] = Field(None, description="API Key for the model")


class AskLLMRequest(TSModel):
    question: str = Field(..., description="The question to ask the model")
    model: ModelMetaRequest
    connection: DBConnectionRequestParams
    stream: bool = Field(True, description="Whether to stream the response or not")
    
    # Storage-related fields (optional for backward compatibility)
    thread_id: Optional[UUID] = Field(None, description="Thread ID for conversation continuity")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the message")
