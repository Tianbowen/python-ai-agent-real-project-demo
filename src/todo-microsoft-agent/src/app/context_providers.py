# app/context_providers.py

from __future__ import annotations

from datetime import date
from typing import Any

from agent_framework import ContextProvider, SessionContext

class TodayDateProvider(ContextProvider):
    """每次模型调用前注入当前日期，让Agent无需猜测今天是几号"""

    def __init__(self) -> None:
        super().__init__(source_id="today_date")

    async def before_run(
        self,
        *,
        agent: Any,
        session: Any,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        today = date.today().isoformat()
        context.extend_instructions(
            self.source_id,
            f"今日的日期是{today}(ISO格式)。回答与日期相关的问题时以此为准。"
        )

class UserNameProvider(ContextProvider):
    """注入当前用户名，让Agent可以个性化称呼用户。"""

    def __init__(self, username: str) -> None:
        super().__init__(source_id="username")
        self._username = username

    async def before_run(
        self,
        *,
        agent: Any,
        session: Any,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        context.extend_instructions(
            self.source_id,
            f"当前用户的名字是「{self._username}」,与用户交谈时可以称呼他的名字。"
        )