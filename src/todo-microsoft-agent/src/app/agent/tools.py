# agent\tools.py
# 工具定义

from __future__ import annotations

from typing import Annotated

from agent_framework import tool
from pydantic import Field

from app.dependencies import todo_service
from app.domain.errors import TodoError

def _serialize_todo(todo) -> dict:
    """把 Todo 转换成合适工具返回的JSON数据"""
    # 把todo这个Pydantic对象转为JSON安全的字典
    return todo.model_dump(mode="json")

# @tool：声明这是给模型用的函数工具
# @tool 会把函数转换成 MAF 可识别的 FunctionTool，框架会根据以下内容生成工具 schema
# - 函数名称 - docstring - 参数类型 - Field(description=...) 默认值
@tool
def create_todo(
    # Annotated + Field(description=...)：帮助模型填对参数
    title: Annotated[str, Field(description="待办标题，例如：提交周报")],
    priority: Annotated[str, Field(description="优先级：low / medium / high, 默认 medium")] = "medium",
    due_date: Annotated[str | None, Field(description="截止日期，格式 YYYY-MM-DD、今天、明天、后天。" "用户使用相对日期时应保持原文，不要自行推算")] = None,
) -> dict: # 返回 dict 模型可据此组织自然语言回复
    """创建一个新的待办事项。"""
    try:
        item = todo_service.create(title=title, priority=priority, due_date=due_date)
        return {
            "ok": True,
            "todo": _serialize_todo(item)
        }
    except (TodoError, ValueError) as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }

@tool
def list_todos(
    status: Annotated[str | None, Field(description="状态过滤：pending 或 completed")] = None,
    priority: Annotated[str | None, Field(description="优先级过滤：low、medium 或 high")] = None,
    due_on: Annotated[str | None, Field(description="截止日期过滤：YYYY-MM-DD、今天、明天或后天")] = None,
    keyword: Annotated[str | None, Field(description="标题关键字")] = None,
) -> dict:
    """按条件查询待办事项；所有参数为空时返回全部待办。"""
    try:
        todos = todo_service.list_todos(
            status=status,
            priority=priority,
            due_on=due_on,
            keyword=keyword,
        )
        return {
            "ok": True,
            "count": len(todos),
            "todos": [ _serialize_todo(todo=todo) for todo in todos ],
        }
    except (TodoError, ValueError) as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
    
@tool
def complete_todo(
    todo_id: Annotated[str, Field(description="需要标记为已完成的待办事项 ID")]
) -> dict:
    """将指定待办事项标记为已完成"""
    try:
        todo = todo_service.complete(todo_id=todo_id)
        return {
            "ok": True,
            "todo": _serialize_todo(todo=todo),
        }
    except (TodoError, ValueError) as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
    
@tool
def update_todo(
    todo_id: Annotated[str, Field(description="需要修改的待办事项ID")],
    title: Annotated[str | None, Field(description="新标题；不修改则不传")] = None,
    priority: Annotated[str | None, Field(description="新优先级：low、medium 或 high")] = None,
    due_date: Annotated[str | None,Field(description="新截止日期：YYYY-MM-DD、今天、明天或后天")] = None,
    status: Annotated[str | None, Field(description="新状态：pending 或 completed")] = None,
) -> dict:
    """修改指定待办的标题、优先级、截止日期或状态。"""
    try:
        todo = todo_service.update(
            todo_id=todo_id,
            title=title,
            priority=priority,
            due_date=due_date,
            status=status,
        )
        return {
            "ok": True,
            "todo": _serialize_todo(todo=todo)
        }
    except (TodoError, ValueError) as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
    
# 模型选择删除工具后，MAF不会立即执行，而是产生 user_input_requests, 等待应用提交批准或拒绝。
@tool(approval_mode="always_require")
def delete_todo(
    todo_id: Annotated[str, Field(description="需要永久删除的待办事项ID")]
) -> dict:
    """永久删除指定待办事项。删除不可撤销，执行前必须由用户批准。"""
    try:
        todo_service.delete(todo_id=todo_id)
        return {
            "ok": True,
            "deleted_id": todo_id,
        }
    except (TodoError, ValueError) as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }