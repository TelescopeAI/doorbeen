from typing import Any

from core.types.ts_model import TSModel


class NodeExecutionOutput(TSModel):
    name: str
    value: Any
