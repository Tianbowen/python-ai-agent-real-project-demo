# workflows/delete_todo_hitl.py

# 属于惰性加载
from __future__ import annotations

from dataclasses import dataclass

from agent_framework import RunContext, workflow

from app.dependencies import todo_service
from app.domain.errors import TodoNotFoundError

@dataclass
class DeleteTodoInput:
    todo_id: str

@dataclass
class DeleteTodoResult:
    action: str  # "deleted" / "cancelled" / "not_found"
    todo_id: str
    title: str | None = None

@workflow
async def delete_todo_hitl_workflow(
    ctx: RunContext,
    payload: DeleteTodoInput,
) -> DeleteTodoResult:
    """删除前请求人工确认；拒绝则不删除"""
    try:
        todo = todo_service.get(payload.todo_id)
    except TodoNotFoundError:
        return DeleteTodoResult(action="not_found", todo_id=payload.todo_id)
    
    confirmed: bool = await ctx.request_info(
        {
            "todo_id": todo.id,
            "title": todo.title,
            "prompt": f"确认删除待办「{todo.title}」吗？",
        },
        bool,
        request_id="delete_confirm",
    )

    if not confirmed:
        return DeleteTodoResult(action="cancelled", todo_id=todo.id, title=todo.title)
    
    todo_service.delete(todo.id)
    return DeleteTodoResult(action="deleted", todo_id=todo.id, title=todo.title)
