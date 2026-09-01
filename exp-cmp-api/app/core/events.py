from typing import Callable

_subscribers: dict[str, list[Callable]] = {}


def subscribe(event_type: str, handler: Callable) -> None:
    listeners = _subscribers.setdefault(event_type, [])
    if handler not in listeners:
        listeners.append(handler)


def publish(event_type: str, **payload) -> None:
    for handler in _subscribers.get(event_type, []):
        handler(**payload)


def reset_bus() -> None:
    _subscribers.clear()