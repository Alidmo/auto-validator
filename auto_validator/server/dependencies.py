from functools import lru_cache

from auto_validator.modules.listener import ListenerModule
from auto_validator.state.manager import StateManager


@lru_cache(maxsize=1)
def get_state_manager() -> StateManager:
    return StateManager()


def get_listener_module() -> ListenerModule:
    return ListenerModule(state_manager=get_state_manager())
