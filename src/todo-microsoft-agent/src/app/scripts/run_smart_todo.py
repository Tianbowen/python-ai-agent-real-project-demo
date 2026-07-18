# scripts/run_smart_todo.py

import asyncio

from app.dependencies import todo_service
from app.workflows.smart_todo import SmartTodoInput, smart_todo_workflow

async def main() -> None:
    # 第一次：应创建
    first = await smart_todo_workflow.run(
        SmartTodoInput(title="提交周报", priority="high", due_date="明天")
    )
    print("第一次：", first.get_outputs()[0])

    second = await smart_todo_workflow.run(
        SmartTodoInput(title="提交周报")
    )
    print("第二次：", second.get_outputs()[0])

    print("\n当前待办：")
    for todo in todo_service.list_todos():
        print(
            f"- [{todo.status.value}] {todo.title} "
            f"(priority={todo.priority.value})"
        )

if __name__ == "__main__":
    asyncio.run(main())