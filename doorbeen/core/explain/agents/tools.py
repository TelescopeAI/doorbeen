from typing import Optional

from doorbeen.core.agents.tools.parsers.chunk import ToolInvocation
from doorbeen.core.types.ts_model import TSModel


class ExplainToolInvoke(TSModel):
    invocation: ToolInvocation
    explanation: Optional[str] = None

    def explain(self):
        # Logic to determine explanation based on invocation
        return self.explanation
