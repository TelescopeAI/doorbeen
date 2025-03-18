from typing import Optional

from core.agents.tools.parsers.chunk import ToolInvocation
from core.types.ts_model import TSModel


class ExplainToolInvoke(TSModel):
    invocation: ToolInvocation
    explanation: Optional[str] = None

    def explain(self):
        # Logic to determine explanation based on invocation
        return self.explanation
