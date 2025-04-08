from typing import Optional

from pydantic import Field

from doorbeen.core.types.manufacturers import ModelProviders
from doorbeen.core.types.ts_model import TSModel


class ModelMeta(TSModel):
    name: str = Field(..., description="The name of the language model")
    provider: ModelProviders = Field(..., description="The manufacturer of the language model to determine the SDK")
    version: Optional[str] = Field(None, description="The version of the language model")
    description: Optional[str] = Field(None, description="A brief description of the language model")
    metadata: Optional[dict] = Field(None, description="Any additional metadata related to the model")


class ModelInstance(ModelMeta):
    api_key: Optional[str] = Field(None, description="API Key for the model")


if __name__ == "__main__":
    # Example usage
    model = ModelMeta(
        name="GPT-4",
        provider=ModelProviders.OPENAI,
        version="4.0",
        description="Generative Pre-trained Transformer 4",
        metadata={"parameters": "175B", "use_cases": ["chatbots", "content generation"]}
    )

    print(model.json())
