from typing import Optional, Any

from pydantic import Field, field_validator

from core.config.execution_env import ExecutionEnv
from core.types.ts_model import TSModel


class PGLocationConfig(TSModel):
    autocommit: bool = Field(True, description="Whether to autocommit the transactions")
    prepare_threshold: Optional[int] = Field(0, description="The threshold for preparing the transactions")


class PostgresLocation(TSModel):
    db_uri: str = Field(None, description="The URI of the PostgreSQL database")
    config: Optional[PGLocationConfig] = Field(default_factory=PGLocationConfig, description="The configuration for the PostgreSQL connection")