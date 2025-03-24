from typing import Optional

from pydantic import Field
from pydantic import Field as FieldV2

from core.types.databases import DatabaseTypes
from core.types.ts_model import TSModel


class DBConnectionRequestParams(TSModel):
    db_type: DatabaseTypes
    credentials: dict = Field(..., description="The credentials for the database connection")


class ModelMetaRequest(TSModel):
    name: str = Field(..., description="The name of the language model")
    api_key: Optional[str] = Field(None, description="API Key for the model")


class AskLLMRequest(TSModel):
    question: str = Field(..., description="The question to ask the model")
    model: ModelMetaRequest
    connection: DBConnectionRequestParams
    stream: bool = Field(False, description="Whether to stream the response or not")


class DBConnectionRequestParamsV2(TSModel):
    db_type: DatabaseTypes
    credentials: dict = FieldV2(
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


class ModelMetaRequestV2(TSModel):
    name: str = FieldV2(..., description="The name of the language model")
    api_key: Optional[str] = FieldV2(None, description="API Key for the model")


class AskLLMRequestV2(TSModel):
    question: str = FieldV2(..., description="The question to ask the model")
    model: ModelMetaRequestV2
    connection: DBConnectionRequestParamsV2
    stream: bool = FieldV2(False, description="Whether to stream the response or not")
