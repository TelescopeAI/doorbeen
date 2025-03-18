from typing import List, Dict, Any
from pydantic import Field
from core.types.ts_model import TSModel


class ModelUsageStats(TSModel):
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0


class ModelUsage(TSModel):
    model_name: str
    input: str
    output: str
    stats: ModelUsageStats


class ModelUsageTracker(TSModel):
    usages: List[Dict[str, Any]] = Field(default_factory=list)

    def add_usage(self, model_name: str, input: str, output: str, stats: Dict[str, Any]):
        usage = {
            "model_name": model_name,
            "input": input,
            "output": output,
            "stats": ModelUsageStats(**stats).model_dump()
        }
        self.usages.append(usage)

    def get_total_usage(self) -> ModelUsageStats:
        return ModelUsageStats(
            total_tokens=sum(usage["stats"]["total_tokens"] for usage in self.usages),
            prompt_tokens=sum(usage["stats"]["prompt_tokens"] for usage in self.usages),
            completion_tokens=sum(usage["stats"]["completion_tokens"] for usage in self.usages),
            total_cost=sum(usage["stats"]["total_cost"] for usage in self.usages)
        )

    def get_usage_by_model(self) -> Dict[str, ModelUsageStats]:
        usage_by_model = {}
        for usage in self.usages:
            model_name = usage["model_name"]
            if model_name not in usage_by_model:
                usage_by_model[model_name] = ModelUsageStats()
            model_stats = usage_by_model[model_name]
            model_stats.total_tokens += usage["stats"]["total_tokens"]
            model_stats.prompt_tokens += usage["stats"]["prompt_tokens"]
            model_stats.completion_tokens += usage["stats"]["completion_tokens"]
            model_stats.total_cost += usage["stats"]["total_cost"]
        return usage_by_model
