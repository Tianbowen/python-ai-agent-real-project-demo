# services/todo_service.py

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.domain.errors import TodoNotFoundError, TodoValidationError
from app.domain.models import Todo, TodoQuery, TodoCreate, TodoUpdate, Priority, TodoStatus

from app.repositories.base import TodoRepository

class TodoService:
    def __init__(self, repo: TodoRepository) -> None:
        self._repo = repo

    def create(self, title: str, priority: str = "medium", due_date: str | None = None, *, today: date | None = None) -> Todo:
        cleaned = title.strip()
        if not cleaned:
            raise TodoValidationError("标题不能为空")
        
        try:
            p = Priority(priority.lower())
        except Exception as exc:
            raise TodoValidationError("priority 必须是 low/medium/high") from exc
        
        parsed_due = self.parse_due_date(due_date, today=today)
        todo = Todo(title=cleaned, priority=p, due_date=parsed_due)
        return self._repo.add(todo=todo)
    
    def list_todos(self, status: str | None = None, priority: str | None = None, due_on: str | None = None, keyword: str | None = None, *, today: date | None = None) -> list[Todo]:
        query = TodoQuery(status= TodoStatus(status) if status else None, priority=Priority(priority) if priority else None, due_on = self.parse_due_date(due_on, today=today) if due_on else None, keyword=keyword)
        return self._repo.list(query=query)
    
    def get(self, todo_id: str) -> Todo:
        todo = self._repo.get(todo_id=todo_id)
        if not todo:
            raise TodoNotFoundError(todo_id=todo_id)
        return todo
    
    def complete(self, todo_id: str, *, completed_at: datetime | None = None) -> Todo:
        todo = self.get(todo_id=todo_id)
        todo.mark_completed(completed_at=completed_at)
        return self._repo.update(todo=todo)
    
    def update(self, todo_id: str, *, title: str | None = None, priority: str | None = None, due_date: str | None = None, status: str | None = None, today: date | None = None) -> Todo:
        todo = self.get(todo_id=todo_id)
        patch = TodoUpdate(
            title=title.strip() if title else None,
            priority=Priority(priority) if priority else None,
            due_date=self.parse_due_date(due_date, today=today) if due_date else None,
            status=TodoStatus(status) if status else None,
        )
        data = todo.model_dump()
        for key, value in patch.model_dump(exclude_none=True).items():
            data[key] = value
        data['updated_at']= datetime.now(timezone.utc)
        return self._repo.update(Todo.model_validate(data))
    
    def delete(self, todo_id: str) -> None:
        if not self._repo.delete(todo_id=todo_id):
            raise TodoNotFoundError(todo_id=todo_id)
        
    def batch_complete(self, todo_ids: list[str]) -> list[Todo]:
        return [self.complete(todo_id=todo_id) for todo_id in todo_ids]
    
    def today_summary(self, *, today: date | None = None) -> dict:
        day = today or date.today()
        pending = self.list_todos(status=TodoStatus.PENDING.value)
        due_today = [t for t in pending if t.due_date == day]
        overdue = [t for t in pending if t.due_date and t.due_date < day]
        completed_today = [
            t
            for t in self.list_todos(status=TodoStatus.COMPLETED.value)
            if t.updated_at.date() == day
        ]
        return {
            "date": day.isoformat(),
            "pending_count": len(pending),
            "due_today_count": len(due_today),
            "overdue_count": len(overdue),
            "completed_today_count": len(completed_today),
            "due_today": due_today,
            "overdue": overdue,
        }
    
    @staticmethod
    def parse_due_date(value: str | None, *, today: date | None = None) -> date | None:
        if value is None or value.strip() == "":
            return None
        
        text = value.strip().lower()
        base = today or date.today()

        aliases = {
            "today": base,
            "今天": base,
            "tomorrow": base + timedelta(days=1),
            "明天": base + timedelta(days=1),
            "day after tomorrow": base + timedelta(days=2),
            "后天": base + timedelta(days=2),
        }
        if text in aliases:
            return aliases[text]
        
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise TodoValidationError(f"无法解析日期：{value}，请使用 YYYY-MM-DD 或 今天/明天/后天") from exc

        
        