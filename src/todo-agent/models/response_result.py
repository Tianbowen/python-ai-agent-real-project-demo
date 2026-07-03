# models/response_result.py
# 

from dataclasses import dataclass, field
from typing import Any, List

SUCCEED_CODE = "200"

@dataclass
class ResponseResult:
    """统一 API响应结构"""

    code: str = SUCCEED_CODE
    message: str = "成功"
    succeed: bool = True
    result: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "succeed": self.succeed,
            "result": self.result,
        }
    
    @classmethod
    def ok(cls, biz_code: str, answer: str, data: List = None) -> "ResponseResult":
        return cls(result={
            "bizCode": biz_code,
            "answer": answer,
            "type": 0,
            "data": data or []
        })
    
    @classmethod
    def error(cls, message: str) -> "ResponseResult":
        return cls(code="500", message=message, succeed=False, result={
            "answer": message, "type": 0, "data": []
        })