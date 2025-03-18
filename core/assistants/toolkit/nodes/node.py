from typing import List, Any

from langgraph.prebuilt import ToolNode


class TSToolNode(ToolNode):
    tools: List[Any]

    def get_node(self):
        return ToolNode(self.tools)
