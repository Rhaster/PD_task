# core/registry.py
from __future__ import annotations
from typing import Iterable, Set, Protocol, runtime_checkable, Optional
from threading import Lock


@runtime_checkable
class NameRegistry(Protocol):
    def exists(self, name: str) -> bool: ...
    def add(self, name: str) -> None: ...
    def existing(self) -> Iterable[str]: ...


class InMemoryNameRegistry(NameRegistry):
    """
    Prosty, bezpieczny w wątkach rejestr nazw (dla FastAPI workers).
    Idealny do dev/testów; znika po restarcie procesu.
    """
    def __init__(self, initial: Optional[Iterable[str]] = None):
        self._set: Set[str] = set(initial or [])
        self._lock = Lock()

    def exists(self, name: str) -> bool:
        with self._lock:
            return name in self._set

    def add(self, name: str) -> None:
        if not name:
            return
        with self._lock:
            self._set.add(name)

    def existing(self) -> Iterable[str]:
        with self._lock:
            # zwracamy kopię, by nie wyciekał wewn. stan
            return list(self._set)