class BizException(Exception):
    """业务异常：有明确的错误码和用户友好信息"""
    def __init__(self, code: str = "BIZ_ERROR", message: str = "业务处理失败"):
        self.code = code
        self.message = message
        super().__init__(message)

    def __repr__(self):
        return f"BizException(code={self.code}, message:{self.message})"