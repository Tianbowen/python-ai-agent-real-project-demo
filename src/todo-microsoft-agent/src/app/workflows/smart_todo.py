# workflows/smart_todo.py
# 智能待办

from __future__ import annotations

from dataclasses import dataclass

from agent_framework import workflow

from app.dependencies import todo_service
from app.domain.models import TodoStatus

@dataclass
class SmartTodoInput:
    title: str
    priority: str = "medium"
    due_date: str | None = None

@dataclass
class SmartTodoResult:
    action: str # "completed" / "created"
    todo_id: str
    title: str
    status: str

@workflow
async def smart_todo_workflow(payload: SmartTodoInput) -> SmartTodoResult:
    """若存在同名未完成待办则完成，否则创建。"""
    title = payload.title.strip()
    matches = todo_service.list_todos(
        status=TodoStatus.PENDING.value,
        keyword=title,
    )

    exact = [t for t in matches if t.title == title]

    if exact:
        todo = todo_service.complete(exact[0].id)
        return SmartTodoResult(
            action="completed",
            todo_id=todo.id,
            title=todo.title,
            status=todo.status.value,
        )

    todo = todo_service.create(
        title=title,
        priority=payload.priority,
        due_date=payload.due_date,
    )

    return SmartTodoResult(
        action="created",
        todo_id=todo.id,
        title=todo.title,
        status=todo.status.value,
    )