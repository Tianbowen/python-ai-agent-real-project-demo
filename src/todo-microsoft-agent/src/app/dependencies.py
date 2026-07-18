# dependencies.py

from app.repositories.memory_todo_repo import MemoryTodoRepository
from app.services.todo_service import TodoService

todo_repository = MemoryTodoRepository()
todo_service = TodoService(todo_repository)

# 这样Agent工具和测试外的程序入口会使用同一个内存仓库