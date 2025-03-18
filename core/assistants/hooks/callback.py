from contextlib import contextmanager
from typing import Dict, Any, Generator, Union, TypeAlias
from core.types.manufacturers import ModelProviders
from langchain_community.callbacks import get_openai_callback, OpenAICallbackHandler
from core.types.ts_model import TSModel
from pydantic import Field, PrivateAttr


class BaseCallback(TSModel):
    total_tokens: int = Field(default=0)
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_cost: float = Field(default=0.0)

    def update(self, response):
        pass


class AnthropicCallback(BaseCallback):
    def update(self, response):
        self.total_tokens = response.usage.total_tokens
        self.prompt_tokens = response.usage.prompt_tokens
        self.completion_tokens = response.usage.completion_tokens
        # Note: Implement cost calculation based on Anthropic's pricing


class GoogleCallback(BaseCallback):
    def update(self, response):
        # Implement Google-specific usage tracking
        pass


class MicrosoftCallback(BaseCallback):
    def update(self, response):
        # Implement Microsoft-specific usage tracking
        pass


class AmazonCallback(BaseCallback):
    def update(self, response):
        # Implement Amazon-specific usage tracking
        pass


class MistralCallback(BaseCallback):
    def update(self, response):
        # Implement Mistral-specific usage tracking
        pass


class OpenAICallback(BaseCallback):
    _handler: OpenAICallbackHandler = PrivateAttr(default=None)

    @contextmanager
    def __call__(self):
        with get_openai_callback() as cb:
            self._handler = cb
            yield self
        self.update()
        self._handler = None

    def update(self):
        if self._handler:
            self.total_tokens = self._handler.total_tokens
            self.prompt_tokens = self._handler.prompt_tokens
            self.completion_tokens = self._handler.completion_tokens
            self.total_cost = self._handler.total_cost

    def on_llm_start(self, *args, **kwargs):
        self._handler.on_llm_start(*args, **kwargs)

    def on_llm_end(self, *args, **kwargs):
        self._handler.on_llm_end(*args, **kwargs)
        self.update()

    # Add other methods as needed (on_llm_new_token, etc.)


ModelCallback: TypeAlias = Union[OpenAICallback, AnthropicCallback,
GoogleCallback, MicrosoftCallback, AmazonCallback,
MistralCallback, BaseCallback]


class CallbackManager(TSModel):

    @staticmethod
    def get_callback(model_provider: ModelProviders) -> ModelCallback:
        if model_provider == ModelProviders.OPENAI:
            return OpenAICallback()
        elif model_provider == ModelProviders.ANTHROPIC:
            return AnthropicCallback()
        elif model_provider == ModelProviders.GOOGLE:
            return GoogleCallback()
        elif model_provider == ModelProviders.MICROSOFT:
            return MicrosoftCallback()
        elif model_provider == ModelProviders.AMAZON:
            return AmazonCallback()
        elif model_provider == ModelProviders.MISTRAL:
            return MistralCallback()
        else:
            return BaseCallback()

    @staticmethod
    @contextmanager
    def get_callback_context(model_provider: ModelProviders) -> Generator[ModelCallback, None, None]:
        callback = CallbackManager.get_callback(model_provider)
        if isinstance(callback, OpenAICallback):
            with callback:
                yield callback
        else:
            yield callback

    @staticmethod
    def get_usage_from_callback(cb: Any, model_provider: ModelProviders, model_name: str) -> Dict[str, Any]:
        return {
            "model_provider": model_provider,
            "model_name": model_name,
            "total_tokens": getattr(cb, "total_tokens", 0),
            "prompt_tokens": getattr(cb, "prompt_tokens", 0),
            "completion_tokens": getattr(cb, "completion_tokens", 0),
            "total_cost": getattr(cb, "total_cost", 0)
        }
