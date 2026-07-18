# repositories\memory_todo_repo.py

from __future__ import annotations

# 版本一

# from dataclasses import dataclass, field
# from datetime import datetime, timezone
# from uuid import uuid4

# @dataclass
# class TodoItem:
#     id: str
#     title:str
#     completed: bool = False
#     priority: str = 'medium'
#     due_date: str | None = None
#     created_at: str = field(
#         default_factory=lambda: datetime.now(timezone.utc).isoformat()
#     )

# class MemoryTodoRepository:
#     def __init__(self) -> None:
#         self._items: dict[str, TodoItem] = {}

#     def create(self, title: str, priority: str = "medium", due_date: str | None = None) -> TodoItem:
#         item = TodoItem(
#             id=str(uuid4()),
#             title=title.strip(),
#             priority=priority,
#             due_date=due_date,
#         )
#         self._items[item.id] = item
#         return item
    
#     def list_all(self) -> list[TodoItem]:
#         return list(self._items.values())
    

# # 学习阶段先用全局单例；后面会改成依赖注入
# todo_repo = MemoryTodoRepository()

# 版本二

from app.domain.models import Todo, TodoQuery, TodoStatus
from app.repositories.base import TodoRepository

class MemoryTodoRepository(TodoRepository):
    def __init__(self) -> None:
        self._items: dict[str, Todo] = {}

    def add(self, todo: Todo) -> Todo:
        self._items[todo.id] = todo.model_copy(deep=True)
        return self._items[todo.id].model_copy(deep=True)
    
    def get(self, todo_id: str) -> Todo | None:
        todo = self._items.get(todo_id)
        return todo.model_copy(deep=True) if todo else None
    
    def list(self, query: TodoQuery | None = None) -> list[Todo]:
        items = [t.model_copy(deep=True) for t in self._items.values()]
        if not query:
            return items
        
        result: list[Todo] = []
        for todo in items:
            if query.status and todo.status != query.status:
                continue
            if query.priority and todo.priority != query.priority:
                continue
            if query.due_on and todo.due_date != query.due_on:
                continue
            if query.keyword and query.keyword.lower() not in todo.title.lower():
                continue
            result.append(todo)
        return result

    def update(self, todo: Todo) -> Todo:
        if todo.id not in self._items:
            raise KeyError(todo.id)
        self._items[todo.id] = todo.model_copy(deep=True)
        return self._items[todo.id].model_copy(deep=True)
    
    def delete(self, todo_id: str) -> bool:
        return self._items.pop(todo_id, None) is not None
        
# 学习阶段暂保留单例；接 FastAPI 后会改为依赖注入
todo_repo = MemoryTodoRepository()