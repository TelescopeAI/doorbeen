from typing import List


from doorbeen.api.docs.main import DocsRouter
from doorbeen.api.routers.agents import SQLAgentRouter
from doorbeen.api.routers.assistants import AssistantsRouter
from doorbeen.api.routers.samples import SamplesRouter
from doorbeen.api.routers.validators import ValidationRouter

ROUTES: List[dict] = [
    {"router": AssistantsRouter, "enabled": True, "internal": False},
    # {"router": SQLAgentRouter, "enabled": True, "internal": False},
    # {"router": SamplesRouter, "enabled": True, "internal": False},
    # {"router": ValidationRouter, "enabled": True, "internal": False},
    {"router": DocsRouter, "enabled": True, "internal": False},
]

ENABLED_ROUTES = list(filter(lambda route: route["enabled"] is True, ROUTES))
PUBLIC_ROUTES = list(filter(lambda route: route["internal"] is False, ENABLED_ROUTES))
