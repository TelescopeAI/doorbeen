import json
import re
from typing import Any, Optional, Type, Union

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from doorbeen.core.types.ts_model import TSModel


class ModelInvoker(TSModel):
    llm: Optional[Union[ChatOpenAI]] = None

    def process(self, prompt: str, output_model: Optional[Type[TSModel]] = None,
                plaintext: bool = False) -> Any:
        response = self.llm.invoke(prompt)
        content = None
        isJson = not plaintext
        if isinstance(response, AIMessage):
            content = response.content
            if content == '':
                for tool_call in response.tool_calls:
                    content = str(tool_call["args"])
                    if isJson:
                        json_str = re.search(r'`(.*?)`', content, re.DOTALL).group(1)
                        content = json.loads(json_str)
        elif isinstance(response, str):
            content = response
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")

        if plaintext:
            return content

        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse response as JSON: {content}")

        if output_model:
            return output_model(**parsed_content)
        else:
            return parsed_content
