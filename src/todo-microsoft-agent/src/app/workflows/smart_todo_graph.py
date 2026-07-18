# workflows/smart_todo_graph.py

from __future__ import annotations

from dataclasses import dataclass
# 标注永不返回
from typing import Never

from agent_framework import WorkflowBuilder, WorkflowContext, executor

from app.dependencies import todo_service
from app.domain.models import TodoStatus
from app.workflows.smart_todo import SmartTodoInput, SmartTodoResult

@dataclass
class LookupResult:
    """lookup 节点传给 apply 节点的中间消息。"""
    request: SmartTodoInput
    existing_id: str | None

@executor(id="lookup")
async def lookup(
    payload: SmartTodoInput,
    ctx: WorkflowContext[LookupResult],
) -> None:
    """第一步：查找同名未完成待办。"""
    title = payload.title.strip()
    matches = todo_service.list_todos(
        status=TodoStatus.PENDING.value,
        keyword=title,
    )
    exact = next((t for t in matches if t.title == title), None)

    # 发给下游节点
    await ctx.send_message(
        LookupResult(
            request=payload,
            existing_id=exact.id if exact else None,
        )
    )

@executor(id="apply")
async def apply(
    lookup_result: LookupResult,
    ctx: WorkflowContext[Never, SmartTodoResult]
) -> None:
    """第二步：有则完成，无则创建，并产出最终结果。"""
    request = lookup_result.request

    if lookup_result.existing_id:
        todo = todo_service.complete(lookup_result.existing_id)
        action = "completed"
    else:
        todo = todo_service.create(
            title=request.title,
            priority=request.priority,
            due_date=request.due_date,
        )
        action = "created"

    # 工作流最终输出
    await ctx.yield_output(
        SmartTodoResult(
            action=action,
            todo_id=todo.id,
            title=todo.title,
            status=todo.status.value,
        )
    )

def build_smart_todo_graph():
    """构建可被 DevUI 发现的图 Workflow。"""
    return (
        # 组装 Graph
        WorkflowBuilder(
            start_executor=lookup,
            name="SmartTodoGraph",
            description="查找同名待办：存在则完成，不存在则创建。"
        )
        .add_edge(lookup, apply)
        .build()
    )

# 模块级导出，供 DevUI / 脚本直接 import
smart_todo_graph = build_smart_todo_graph()