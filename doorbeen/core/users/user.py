from typing import Any

from doorbeen.core.config.execution_env import ExecutionEnv
from doorbeen.core.types.ts_model import TSModel
from clerk_backend_api import Clerk

clerk_instance = Clerk(bearer_auth=ExecutionEnv.get_key("CLERK_BACKEND_API_KEY"))


class ClerkUser(TSModel):
    id: str
    meta: Any = None
