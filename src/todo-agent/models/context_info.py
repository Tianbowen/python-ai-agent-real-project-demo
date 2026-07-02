# models/context_info.py
# 请求上下文核心

from typing import Any, Optional
from langchain_core.chat_history import InMemoryChatMessageHistory

from models.ce_models import ConversationSession
from models.request_info import RequestInfo

class ContextInfo:
    """
    请求上下文：一次请求的全部运行时状态都挂在这里
    在请求入口创建，贯穿整个处理链路
    """

    def __init__(self, params: dict = None):
        self.request_info = RequestInfo.from_dict(params or {})
        self.ctx: Optional[ConversationSession] = None # 会话状态 (从缓存恢复)
        self._params: dict = {}
        self._result_text: str = ""

    # 临时参数（请求级，不持久化）
    def add_param(self, key: str, value: Any):
        self._params[key] = value

    def get_param(self, key: str, default= None) -> Any:
        return self._params.get(key, default)
    
    def remove_param(self, key: str, default= None) -> Any:
        return self._params.pop(key, default)
    
    # 对话历史 （代理到 ConversationSession）

    @property
    def chat_history(self) -> InMemoryChatMessageHistory:
        if self.ctx:
            return self.ctx.chat_history
        return InMemoryChatMessageHistory()
    
    # LLM 结果
    def set_result_llm(self, text: str):
        self._result_text = text

    def get_result_llm(self) -> str:
        return self._result_text
    
    # 工具名
    def get_tool_name(self) -> str:
        if self.ctx:
            return self.ctx.tool_name
        return 'get_other'