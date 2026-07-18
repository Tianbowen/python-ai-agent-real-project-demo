from datetime import date, datetime, timezone

import pytest

from app.domain.errors import TodoNotFoundError, TodoValidationError
from app.domain.models import Priority, TodoStatus
from app.repositories.memory_todo_repo import MemoryTodoRepository
from app.services.todo_service import TodoService

@pytest.fixture
def service() -> TodoService:
    return TodoService(MemoryTodoRepository())


def test_create_and_list(service: TodoService) -> None:
    today = date(2026, 7, 14)
    todo = service.create("提交周报", priority="high", due_date="明天", today=today)

    assert todo.title == "提交周报"
    assert todo.priority == Priority.HIGH
    assert todo.due_date == date(2026, 7, 15)

    items = service.list_todos()
    assert len(items) == 1


def test_complete_and_summary(service: TodoService) -> None:
    today = date(2026, 7, 14)
    completed_at = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)

    t1 = service.create("A", due_date="今天", today=today)
    service.create("B", due_date="明天", today=today)

    service.complete(t1.id, completed_at=completed_at)
    summary = service.today_summary(today=today)

    assert summary["completed_today_count"] == 1
    assert summary["due_today_count"] == 0
    assert summary["pending_count"] == 1


def test_delete_missing(service: TodoService) -> None:
    with pytest.raises(TodoNotFoundError):
        service.delete("not-exist")


def test_invalid_priority(service: TodoService) -> None:
    with pytest.raises(TodoValidationError):
        service.create("X", priority="urgent")