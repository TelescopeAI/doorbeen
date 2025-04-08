from enum import Enum
from typing import Dict, List, Optional, Type, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import model_validator
from pydantic import Field

from doorbeen.core.assistants.hooks.callback import CallbackManager
from doorbeen.core.types.manufacturers import ModelProviders
from doorbeen.core.types.ts_model import TSModel


class ModelHandler(TSModel):
    model: Optional[Any] = None
    callback: Optional[Any] = None


class ModelSelectionMode(Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"


class ModelInfo(TSModel):
    name: str
    provider: str
    max_tokens: int
    cost_per_1k_tokens: float
    capabilities: List[str]


class ModelProviderConfig(TSModel):
    models: Dict[str, ModelInfo] = Field(default_factory=dict)
    selection_mode: Dict[str, ModelSelectionMode] = Field(default_factory=dict)
    static_model_assignments: Dict[str, str] = Field(default_factory=dict)


# Initialize ModelProvider with default configuration
default_config = ModelProviderConfig(
    models={
        "gpt-3.5-turbo": ModelInfo(
            name="gpt-3.5-turbo",
            provider="OpenAI",
            max_tokens=4096,
            cost_per_1k_tokens=0.002,
            capabilities=["general", "sql", "analysis"]
        ),
        "gpt-4": ModelInfo(
            name="gpt-4",
            provider="OpenAI",
            max_tokens=8192,
            cost_per_1k_tokens=0.06,
            capabilities=["general", "sql", "analysis", "complex_reasoning"]
        ),
        "gpt-4o": ModelInfo(
            name="gpt-4o",
            provider="OpenAI",
            max_tokens=128000,
            cost_per_1k_tokens=0.06,
            capabilities=["general", "sql", "analysis", "complex_reasoning"]
        ),
        "gpt-4o-mini": ModelInfo(
            name="gpt-4o-mini",
            provider="OpenAI",
            max_tokens=8192,
            cost_per_1k_tokens=0.01,
            capabilities=["general", "sql", "analysis"]
        ),
        "claude-2": ModelInfo(
            name="claude-2",
            provider="Anthropic",
            max_tokens=100000,
            cost_per_1k_tokens=0.01,
            capabilities=["general", "sql", "analysis", "long_context"]
        ),
        "gemini-pro": ModelInfo(
            name="gemini-pro",
            provider="Google",
            max_tokens=32768,
            cost_per_1k_tokens=0.0005,
            capabilities=["general", "analysis"]
        )
    }
)


class ModelProvider(TSModel):
    config: ModelProviderConfig = Field(default_factory=ModelProviderConfig)

    @model_validator(mode='before')
    @classmethod
    def initialize_default_config(cls, values):
        if 'config' not in values or not values['config'].models:
            values['config'] = default_config
        return values

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        return self.config.models.get(model_name)

    def list_models(self) -> List[str]:
        return list(self.config.models.keys())

    def get_model_by_capability(self, capability: str) -> List[str]:
        return [model for model, info in self.config.models.items() if capability in info.capabilities]

    def get_model_instance(self, model_name: str, api_key: Optional[str] = None,
                           output_model: Optional[Type[TSModel]] = None,
                           plaintext: bool = False, **kwargs) -> ModelHandler:
        model_info = self.get_model_info(model_name)
        if not model_info:
            raise ValueError(f"Unknown model: {model_name}")

        return self._get_base_model(model_info, api_key, **kwargs)

    def _get_base_model(self, model_info: ModelInfo, api_key: Optional[str] = None, **kwargs) -> ModelHandler:
        if model_info.provider == "OpenAI":
            base_model = ChatOpenAI(model_name=model_info.name, api_key=api_key, **kwargs)
        elif model_info.provider == "Anthropic":
            base_model = ChatAnthropic(model_name=model_info.name, api_key=api_key, **kwargs)
        elif model_info.provider == "Google":
            base_model = ChatGoogleGenerativeAI(model_name=model_info.name, api_key=api_key, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {model_info.provider}")

        # configured_model = self._set_response_mode(base_model, model_info.provider, None,
        #                                            kwargs.get('plaintext', False))
        configured_model = base_model

        callback = CallbackManager.get_callback(ModelProviders(model_info.provider))

        return ModelHandler(model=base_model, callback=callback)

    def _set_response_mode(self, model: BaseChatModel, provider: str, output_model: Optional[Type[TSModel]], plaintext: bool) -> BaseChatModel:
        if plaintext:
            return model

        if provider == "OpenAI":
            if output_model:
                return model.bind_tools([output_model])
            else:
                return model.bind(response_format={"type": "json_object"})

        elif provider == "Anthropic":
            if output_model:
                parser = PydanticOutputParser(pydantic_object=output_model)
                return model.bind(
                    prompt_template="{prompt}\n\n{format_instructions}\n\nResponse:",
                    format_instructions=parser.get_format_instructions(),
                    output_parser=parser
                )
            else:
                return model.bind(
                    prompt_template="{prompt}\n\nRespond with a JSON object.\n\nResponse:"
                )

        elif provider == "Google":
            # Implement Google-specific response mode setting
            # This might involve using specific prompts or parsers
            pass

        return model

    def set_selection_mode(self, task: str, mode: ModelSelectionMode):
        self.config.selection_mode[task] = mode

    def set_static_model(self, task: str, model_name: str):
        if model_name not in self.config.models:
            raise ValueError(f"Unknown model: {model_name}")
        self.config.static_model_assignments[task] = model_name
        self.set_selection_mode(task, ModelSelectionMode.STATIC)

    def select_model(self, task: str, max_tokens: int | None = None, cost_sensitive: bool = False) -> str:
        mode = self.config.selection_mode.get(task, ModelSelectionMode.DYNAMIC)

        if mode == ModelSelectionMode.STATIC:
            if task not in self.config.static_model_assignments:
                raise ValueError(f"No static model assigned for task: {task}")
            return self.config.static_model_assignments[task]

        # Dynamic selection
        suitable_models = self.get_model_by_capability(task)
        if max_tokens:
            suitable_models = [model for model in suitable_models if self.config.models[model].max_tokens >= max_tokens]

        if not suitable_models:
            raise ValueError(f"No suitable model found for task: {task} with max_tokens: {max_tokens}")

        if cost_sensitive:
            return min(suitable_models, key=lambda m: self.config.models[m].cost_per_1k_tokens)
        else:
            return max(suitable_models, key=lambda m: self.config.models[m].max_tokens)
