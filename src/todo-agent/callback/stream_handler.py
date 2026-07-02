# callback/stream_handler.py
# 流式回调（生产者-消费者）

import asyncio
import json
from typing import Any, Optional, Callable, AsyncIterator

from config import logger

class StreamCallbackHandler:
    """
    流式输出控制器

    核心设计模式：生产者-消费者
    - 生产者： LLM 每生成一个 token, 调用 put_token() 放入队里额
    - 消费者： SSE 响应迭代器从队列取出 token,推送给客户端
    """

    _DONE_SENTINEL = object() # 结束标志， 放入队列标识流结束

    def __init__(self, context=None):
        self.context = context
        self._queue = asyncio.Queue = asyncio.Queue(maxsize=200)
        self._error = Optional[str] = None
        self._cancelled: bool = False
        self._ended: bool = False
        self._text_buffer: list[str] = [] # 收集完整LLM输出
        self._callbacks: list[Callable] = [] # 完成回调
        self._biz_data: dict = {} # 业务结构化数据（工具填充）

    # 生产者接口（供工具/LLM调用）
    async def put_token(self, token: str):
        """LLM 生成了一个 token, 加入队列"""
        if self._cancelled or self._ended:
            return
        self._text_buffer.append(token)
        payload = json.dumps({"token": token}, ensure_ascii=False)
        await self._queue.put(payload)

    def set_error(self, message: str):
        """标记错误状态"""
        self._error = message

    def set_canelled(self, flag: bool):
        self_cancelled = flag

    def add_callback(self, fn: Callable):
        """注册完成回调（工具执行完毕后触发）"""
        self._callbacks.append(fn)

    async def end(self):
        """通知消费者流已结束"""
        if not self._ended:
            self._ended = True
            if self._error:
                error_payload = json.dumps(
                    {"error": self._error}, ensure_ascii=False
                )
                await self._queue.put(error_payload)
            await self._queue.put(self._DONE_SENTINEL)

    # 消费者接口（供SSE 响应迭代器调用）

    async def aiter(self) -> AsyncIterator[str]:
        """异步迭代器：逐个取出队列中的 token/数据块"""
        while True:
            item = await self._queue.get()
            if item is self._DONE_SENTINEL:
                break
            yield item

    # 查询接口

    def get_full_text(self) -> str:
        return "".join(self._text_buffer)
    
    def get_biz_data(self) -> dict:
        return self._biz_data
    
    def is_error(self) -> bool:
        return self._error is not None
    
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def fire_callbacks(self):
        """触发所有完成回调"""
        for fn in self._callbacks:
            try:
                fn()
            except Exception as e:
                logger.error(f"回调执行失败：{e}")

        