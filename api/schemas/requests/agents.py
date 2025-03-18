from typing import Optional

from pydantic import Field as FieldV2
from pydantic import Field

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
    credentials: dict = FieldV2(..., description="The credentials for the database connection")


class ModelMetaRequestV2(TSModel):
    name: str = FieldV2(..., description="The name of the language model")
    api_key: Optional[str] = FieldV2(None, description="API Key for the model")


class AskLLMRequestV2(TSModel):
    question: str = FieldV2(..., description="The question to ask the model")
    model: ModelMetaRequestV2
    connection: DBConnectionRequestParamsV2
    stream: bool = FieldV2(False, description="Whether to stream the response or not")
