# test_agent_tools.py

import json

import pytest

from app.agent import tools
from app.domain.models import TodoStatus
from app.repositories.memory_todo_repo import MemoryTodoRepository
from app.services.todo_service import TodoService
from app.domain.errors import TodoNotFoundError


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> TodoService:
    service = TodoService(MemoryTodoRepository())

    # 让工具使用测试专属 Service，避免污染程序的全局数据
    monkeypatch.setattr(tools, "todo_service", service)
    return service


async def invoke_tool(function_tool, arguments: dict) -> dict:
    """通过 MAF FunctionTool 的正式调用入口执行工具。"""
    contents = await function_tool.invoke(arguments=arguments)

    assert len(contents) == 1
    assert contents[0].type == "text"
    assert contents[0].text is not None

    return json.loads(contents[0].text)


async def test_create_and_list_tools(service: TodoService) -> None:
    created = await invoke_tool(
        tools.create_todo,
        {
            "title": "提交周报",
            "priority": "high",
            "due_date": "明天",
        },
    )

    assert created["ok"] is True
    assert created["todo"]["title"] == "提交周报"
    assert created["todo"]["priority"] == "high"

    listed = await invoke_tool(tools.list_todos, {})

    assert listed["ok"] is True
    assert listed["count"] == 1
    assert listed["todos"][0]["id"] == created["todo"]["id"]


async def test_complete_tool(service: TodoService) -> None:
    todo = service.create("提交周报")

    completed = await invoke_tool(
        tools.complete_todo,
        {"todo_id": todo.id},
    )

    assert completed["ok"] is True
    assert completed["todo"]["status"] == "completed"
    assert service.get(todo.id).status == TodoStatus.COMPLETED


async def test_complete_missing_todo(service: TodoService) -> None:
    result = await invoke_tool(
        tools.complete_todo,
        {"todo_id": "not-exist"},
    )

    assert result["ok"] is False
    assert result["error"] == "TodoNotFoundError"

async def test_update_tool(service: TodoService) -> None:
    todo = service.create(
        title="提交周报",
        priority="medium",
    )

    result = await invoke_tool(
        tools.update_todo,
        {
            "todo_id": todo.id,
            "title": "提交月报",
            "priority": "high",
            "due_date": "明天",
        },
    )

    assert result["ok"] is True
    assert result["todo"]["title"] == "提交月报"
    assert result["todo"]["priority"] == "high"
    assert result["todo"]["due_date"] is not None

    saved = service.get(todo.id)
    assert saved.title == "提交月报"
    assert saved.priority.value == "high"


async def test_update_missing_todo(service: TodoService) -> None:
    result = await invoke_tool(
        tools.update_todo,
        {
            "todo_id": "not-exist",
            "title": "新标题",
        },
    )

    assert result["ok"] is False
    assert result["error"] == "TodoNotFoundError"

def test_delete_tool_requires_approval() -> None:
    assert tools.delete_todo.approval_mode == "always_require"


async def test_delete_tool_contract(service: TodoService) -> None:
    todo = service.create("准备删除的任务")

    result = await invoke_tool(
        tools.delete_todo,
        {"todo_id": todo.id},
    )

    assert result["ok"] is True
    assert result["deleted_id"] == todo.id

    with pytest.raises(TodoNotFoundError):
        service.get(todo.id)
