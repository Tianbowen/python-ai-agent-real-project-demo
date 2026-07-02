# agents/abstract_tool.py
# 智能体工具层

from abc import ABC, abstractmethod
from typing import Any

from callback.stream_handler import StreamCallbackHandler
from models.context_info import ContextInfo

class AbstractTool(ABC):
    """
    智能体工具基类
    每个业务能力 = 一个继承此类的子类

    核心接口：
    - name / description: 工具元信息(用于注册和LLM理解)
    - arun(): 异步执行工具
    """

    name: str = "" # 工具唯一标识（与 tasks.yaml 中的 tool 字段对应）
    description: str = "" # 工具功能描述

    def __init__(self, handler: StreamCallbackHandler = None):
        self.handler = handler

    @property
    def context(self) -> ContextInfo:
        return self.handler.context
    
    @abstractmethod
    async def arun(self, query: str, **kwargs) -> str:
        """
        执行工具主逻辑
        通过 self.handler.put_token() 推送流式内容
        返回一个完成标记字符串（不是最总答案，答案通过handler 推送）
        """
        ...