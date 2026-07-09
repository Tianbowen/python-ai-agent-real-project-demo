# dispatch/dispatcher.py
# 总调度器

# 内置异步
import asyncio
import json
import time 
# AsyncIterable 异步迭代器 async | 
# Optional 可选类型 某个类型 | None = str | None 3.10后新写法
from typing import AsyncIterable, Optional

from fastapi import Request
from sse_starlette import EventSourceResponse

from callback.stream_handler import StreamCallbackHandler
from common.exceptions import BizException
from config import MAX_CONCURRENCY, CHAT_TIMEOUT_S, logger
from context_engine.engine import context_manager
from models.context_info import ContextInfo
from models.response_result import ResponseResult, SUCCEED_CODE

# 并发限流信号量（整个进程共享）
_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENCY)

_ERROR_MSG = "抱歉，服务暂时繁忙，请稍后重试"
_BUSY_MSG = "当前服务人数较多，请稍后再试"

class Dispatcher:
    """
    总调度器：处理一次完整的对话请求

    流程：
    1. 并发控制（Semaphore）
    2. 参数解析 -> ContextInfo
    3. 合规校验（空值/敏感词）
    4. 上下文工程（主题/任务识别）
    5. 路由到对应工具执行
    6. SSE 流式响应 / 同步响应
    """

    # 步骤1 并发控制
    async def _acquire(self) -> bool:
        try:
            await asyncio.wait_for(_SEMAPHORE.acquire(), timeout=1.0)
            return True
        except asyncio.TimeoutError:
            return False
        
    def _release(self):
        _SEMAPHORE.release()

    # 步骤2 参数解析
    def _build_context(self, data: dict) -> ContextInfo:
        """把 HTTP 请求 body 解析成 ContextInfo"""
        mapped = {
            "query": data.get("query", ""),
            "bizCode": data.get("bizCode", "agents"),
            "conversationId": data.get("conversationId", ""),
        }
        return ContextInfo(mapped)
    
    # 步骤3 合规校验

    def _validate(self, context: ContextInfo) -> Optional[str]:
        query = context.request_info.query()
        if not query:
            return "您输入的内容为空，请重新输入"
        if len(query) > 500:
            return "输入内容过长，请控制在 500 字以内"
        return None
    
    # 核心调度

    async def _run(self, data: dict) -> StreamCallbackHandler:
        """
        构建 context -> 上下文工程 -> 工具执行, 返回 handler
        """

        context = self._build_context(data)
        handler = StreamCallbackHandler(context=context)

        # 合规校验
        error_msg = self._validate(context=context)
        if error_msg:
            handler.set_error(error_msg)
            await handler.end()
            return handler
        
        # 上下文工程（同步调用， 在线程池里执行避免阻塞事件循环）
        try:
            await asyncio.to_thread(
                context_manager.handle,
                context.request_info.query(),
                context,
            )
        except Exception as e:
            logger.exception(f"上下文工程失败：{e}")
            handler.set_error(_ERROR_MSG)
            return handler
        
        # need_confirm: 本轮需要用户确认，推提示后直接结束，不执行工具
        if context.get_param("need_confirm"):
            confirm_msg = context.get_param("need_confirm_msg", "请确认是否继续操作？")
            await handler.put_token(confirm_msg)
            await handler.put_data(
                biz_code=context.request_info.biz_code(),
                answer=confirm_msg,
                data=[],
            )
            await handler.end()
            return handler
        
        # confirm_aborted: 用户取消，推提示后直接结束
        if context.get_param("confirm_aborted"):
            abort_msg = "操作已取消，待办列表未做任何修改。"
            await handler.put_token(abort_msg)
            await handler.put_data(
                biz_code=context.request_info.biz_code(),
                answer=abort_msg,
                data=[],
            )
            await handler.end()
            return handler


        # 路由到工具并异步执行
        tool_name = context.get_tool_name()
        logger.info(f"路由到工具：{tool_name}")

        asyncio.create_task(
            self._execute_tool(tool_name, context, handler)
        )

        return handler
    
    async def _execute_tool(self, tool_name: str, context: ContextInfo, handler: StreamCallbackHandler):
        """执行工具（在后台Task中执行）"""
        from agents.tool_registry import ToolRegistry
        from dispatch.process_proxy import ProcessProxy

        # 确认流程：用保存的原始 query 替代用户说的 "确认" 两个字
        effective_query = context.get_param("confirmed_query") or context.request_info.query()

        class _Proxy(ProcessProxy):
            async def do_process(self, query: str, **kwargs):
                tool = ToolRegistry.get(tool_name, self.handler)
                await tool.arun(effective_query, **kwargs)

        proxy = _Proxy(
            biz_code=context.request_info.biz_code(),
            handler= handler,
        )
                
        try:
            await proxy.aprocess()
        except BizException as e:
            handler.set_error(e.message)
            await handler.end()
        except Exception as e:
            logger.exception(f"工具执行异常:{e}")
            handler.set_error(_ERROR_MSG)
            await handler.end()
    
    async def dispatch_stream(self, data: dict, request: Request) -> EventSourceResponse:
        """SSE 流式响应（推荐,用于对话界面）"""
        if not await self._acquire():
            logger.warning("并发超限，拒绝请求")
            async def _busy():
                yield json.dumps({"error": _BUSY_MSG}, ensure_ascii=False)
                yield "[DONE]"
            return EventSourceResponse(_busy(), ping=10)
        
        try:
            handler = await self._run(data)
        except Exception as e:
            self._release()
            # 主动抛出异常
            raise e
        
        async def _stream():
            try:
                async for chunk in handler.aiter():
                    yield chunk
                yield "[DONE]"
            finally:
                self._release()

        return EventSourceResponse(_stream(), ping=10)
    
    async def dispatch_sync(self, data: dict) -> dict:
        """同步响应（用于测试或简单场景）"""
        if not await self._acquire():
            return ResponseResult.error(_BUSY_MSG).to_dict()
        
        try:
            handler = await self._run(data=data)
            # 等待所有 token 生成完毕
            async for _ in handler.aiter():
                pass
            return ResponseResult.ok(biz_code=data.get("bizCode", "agents"),answer=handler.get_full_text()).to_dict()
        finally:
            self._release()

# 模块提供单例
dispatcher = Dispatcher()