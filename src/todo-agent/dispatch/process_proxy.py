# dispatch/process_proxy.py
# 调度器（完整请求流程）

# 内置异步库
import asyncio

# 创建 "抽象基类"(接口蓝图)，强制要求子类必须实现特定方法
# ABC 抽象基类标记， 定义类需要继承 ABC 成为 抽象基类
# @abstractmethod 抽象方法修饰器 只有方法名和参数，没有具体实现 或 只有pass+
# 继承的语法
# class 子类名(父类名):
#     pass
from abc import ABC, abstractmethod

from cache.cache import set_session
from callback.stream_handler import StreamCallbackHandler
from config import logger
from models.context_info import ContextInfo

class ProcessProxy(ABC):
    """
    工具执行代理基类
    负责：前置准备 -> 执行工具 -> 后置处理(持久化/摘要)
    """

    # __init__ 被 news实例时 构造函数
    def __init__(self, biz_code: str, handler: StreamCallbackHandler):
        # 属性声明 并不需要提前 动态语言的特性
        self.biz_code = biz_code
        self.handler = handler
        
    # 只读的宽街属性 可 obj.context直接获取内部内向的。本质：代理 或 快捷方式
    @property
    def context(self) -> ContextInfo:
        return self.handler.context
    
    @abstractmethod
    # **kwargs 所有未被显示定义 防止接口入参爆炸 父类不知道子类需要什么
    # 例如查天气 需要 date city
    # 发邮件 需要 title content by
    # 用法一 用 get(key名， 默认值)
    # 用法二 **kwargs 全部展开 
    # 用法三 剔除某个参数 pop(key名)
    async def do_process(self, query: str, **kwargs):
        """子类实现具体的工具执行逻辑"""
        ...

    async def post_process(self):
        """后置处理：记录对话历史，保存会话"""
        ctx = self.context
        query = ctx.request_info.query()
        answer = ctx.get_result_llm()

        if ctx.ctx and answer:
            # 追加到对话历史
            ctx.ctx.add_history(query, answer=answer)
            # 保存会话到缓存(实现多轮记忆)
            biz_code = ctx.request_info.biz_code()
            session_id = ctx.request_info.conversation_id()
            cache_key = f"{biz_code}:{session_id}"
            set_session(cache_key, ctx.ctx)
            logger.debug(f"会话已保存：{cache_key}, history_len={len(ctx.ctx.chat_history.messages)}")

    async def aprocess(self, **kwargs):
        """完整处理流程"""
        query = self.context.request_info.query()
        try:
            await self.do_process(query=query, **kwargs)
        finally:
            await self.handler.end()
            # 后置处理（fire-and-forget, 不影响响应速度）
            asyncio.create_task(self.post_process())
