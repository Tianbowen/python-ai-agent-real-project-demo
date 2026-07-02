# models/request_info.py

from dataclasses import dataclass, field
from typing import Any

@dataclass
class RequestInfo:
    """
        封装单次 HTTP 请求的所有入参

    """

    params: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "RequestInfo":
        ri = cls()
        ri.params = dict(data)
        return ri
    
    # 常用参数快捷访问
    def query(self) -> str:
        """用户这轮输入的文本"""
        return str(self.params.get("query", "")).strip()
    
    def biz_code(self) -> str:
        """业务场景编码，对应task.yaml的key"""
        return str(self.params.get("bizCode", "agents")).strip()
    
    def conversation_id(self) -> str:
        """
        会话ID: 标识"同一个会话"
        同一个 conversation_id 的多轮请求共享历史记录
        前端负责生成并在每次请求中携带        
        """
        return str(self.params.get("conversationId", "")).strip()
    
    def user_id(self) -> str:
        """用户唯一标识（用于区分不同用户的数据）"""
        return str(self.params.get("userId", "")).strip()
    
    def get(self, key: str, default: Any = None) -> Any:
        """通用参数获取"""
        return self.params.get(key, default)