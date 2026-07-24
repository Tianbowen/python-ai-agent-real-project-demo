# app/middleware.py

from __future__ import annotations

import time
from typing import Any

import json

from agent_framework import (
    FunctionInvocationContext,
    FunctionMiddleware,
    MiddlewareTermination,
    function_middleware,
)

# 写法一：装饰器（适合简单场景）
@function_middleware
async def tool_audit_middleware(
    context: FunctionInvocationContext,
    call_next: Any,
) -> None:
    """记录每次工具调用的入参与出参。"""
    print(f"[AUDIT] ▶ {context.function.name} args={context.arguments}")
    try:
        await call_next()
    finally:        
        print(f"[AUDIT] ◀ {context.function.name} result={context.result}")

# 写法二：类（需要构造参数时用）
class TimingMiddleware(FunctionMiddleware):
    """记录每次工具调用耗时（毫秒）。"""

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Any,
    ) -> None:
        start = time.perf_counter()
        await call_next()
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[TIMING] {context.function.name} took {elapsed_ms:.1f}ms")

class ReadOnlyGuardMiddleware(FunctionMiddleware):
    """演示拦截：禁止写操作工具，调用时直接终止并返回提示。"""

    _WRITE_TOOLS = {"create_todo", "complete_todo", "update_todo", "delete_todo"}

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Any,
    ) -> None:
        if context.function.name in self._WRITE_TOOLS:
            # 版本一 设置 result 后 raise MiddlewareTermination 跳过实际执行
            # context.result = f"[只读模式] 工具 {context.function.name} 已被拦截，不允许写操作。"

            # 版本二：属于模型行为调优。把拦截文字改为更像"错误"的格式，让模型更容易识别。
            context.result = json.dumps(
                {"error": "PERMISSION_DENIED", "message": f"工具 {context.function.name} 已被拒绝，系统处于只读模式"},
                ensure_ascii=False,
            )
            raise MiddlewareTermination()
        await call_next()