from enum import Enum


class ModelProviders(str, Enum):
    OPENAI = "OpenAI"
    GOOGLE = "Google"
    MICROSOFT = "Microsoft"
    AMAZON = "Amazon"
    ANTHROPIC = "Anthropic"
    MISTRAL = "MISTRAL"
