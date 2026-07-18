# repositories/base.py

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import Todo, TodoQuery

class TodoRepository(ABC):
    @abstractmethod
    def add(self, todo: Todo) -> Todo: ...

    @abstractmethod
    def get(self, todo_id: str) -> Todo | None: ...

    @abstractmethod
    def list(self, query: TodoQuery) -> list[Todo]: ...

    @abstractmethod
    def update(self, todo: Todo) -> Todo: ...

    @abstractmethod
    def delete(self, todo_id: str) -> bool: ...