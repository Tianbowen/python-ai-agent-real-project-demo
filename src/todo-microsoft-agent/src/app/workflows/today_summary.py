# workflows/today_summary.py

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date

from agent_framework import workflow

from app.dependencies import todo_service
from app.domain.models import TodoStatus

@dataclass
class SummaryInput:
    """workflow的输入"""
    today: str | None = None # YYYY-MM-DD; 为空则用系统今天

@dataclass
class SummaryResult:
    date:str
    pending_count: int
    due_today_count: int
    overdue_count: int
    completed_today_count: int
    due_today_titles: list[str]
    overdue_titles: list[str]

async def _count_pending() -> int:
    return len(todo_service.list_todos(status=TodoStatus.PENDING.value))

async def _count_completed_today(day: date) -> int:
    completed = todo_service.list_todos(status=TodoStatus.COMPLETED.value)
    return sum(1 for t in completed if t.updated_at.date() == day)

@workflow
async def today_summary_workflow(payload: SummaryInput) -> SummaryResult:
    """并行统计今日待办摘要"""
    day = date.fromisoformat(payload.today) if payload.today else date.today()

    # asyncio.gather：并行执行两个统计步骤
    pending_count, completed_today_count = await asyncio.gather(
        _count_pending(),
        _count_completed_today(day=day),
    )

    pending = todo_service.list_todos(status=TodoStatus.PENDING.value)
    due_today = [t for t in pending if t.due_date == day]
    overdue = [t for t in pending if t.due_date and t.due_date < day]

    return SummaryResult(
        date=day.isoformat(),
        pending_count=pending_count,
        due_today_count=len(due_today),
        overdue_count=len(overdue),
        completed_today_count=completed_today_count,
        due_today_titles=[t.title for t in due_today],
        overdue_titles=[t.title for t in overdue],
    )
