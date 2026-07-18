# domain/models.py
# 领域模型

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TodoStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"

class Todo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    priority: Priority = Priority.MEDIUM
    status: TodoStatus = TodoStatus.PENDING
    due_date: date | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_completed(self, *, completed_at: datetime | None = None) -> None:
        self.status = TodoStatus.COMPLETED
        self.updated_at = completed_at or datetime.now(timezone.utc)

class TodoCreate(BaseModel):
    title: str
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None

class TodoUpdate(BaseModel):
    title: str | None = None
    priority: Priority | None = None
    due_date: date | None = None
    status: TodoStatus | None = None

class TodoQuery(BaseModel):
    status: TodoStatus | None = None
    priority: Priority | None = None
    due_on: date | None = None
    keyword: str | None = None
