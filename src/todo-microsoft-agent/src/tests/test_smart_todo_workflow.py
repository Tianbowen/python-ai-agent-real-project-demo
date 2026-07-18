import pytest

from app.repositories.memory_todo_repo import MemoryTodoRepository
from app.services.todo_service import TodoService
from app.workflows import smart_todo
from app.workflows.smart_todo import SmartTodoInput, smart_todo_workflow


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> TodoService:
    service = TodoService(MemoryTodoRepository())
    monkeypatch.setattr(smart_todo, "todo_service", service)
    return service


async def test_smart_todo_create_then_complete(service: TodoService) -> None:
    created = await smart_todo_workflow.run(
        SmartTodoInput(title="提交周报", priority="high")
    )
    assert created.get_outputs()[0].action == "created"

    completed = await smart_todo_workflow.run(
        SmartTodoInput(title="提交周报")
    )
    assert completed.get_outputs()[0].action == "completed"