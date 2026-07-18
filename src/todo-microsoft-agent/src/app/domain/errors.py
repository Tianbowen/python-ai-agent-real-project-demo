# domain/errors.py
# 领域异常

class TodoError(Exception):
    """待办业务错误基类。"""

class TodoNotFoundError(TodoError):
    def __init__(self, todo_id: str) -> None:
        self.todo_id = todo_id
        super().__init__(f"Todo not found: {todo_id}")

class TodoValidationError(TodoError):
    pass
        