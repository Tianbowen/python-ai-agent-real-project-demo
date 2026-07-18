import asyncio

from app.dependencies import todo_service
from app.workflows.smart_todo import SmartTodoInput
from app.workflows.smart_todo_graph import smart_todo_graph


async def main() -> None:
    first = await smart_todo_graph.run(
        SmartTodoInput(title="整理笔记", priority="medium", due_date="今天")
    )
    print("第一次:", first.get_outputs()[0])

    second = await smart_todo_graph.run(
        SmartTodoInput(title="整理笔记")
    )
    print("第二次:", second.get_outputs()[0])

    print("\n当前待办:")
    for todo in todo_service.list_todos():
        print(f"- [{todo.status.value}] {todo.title}")


if __name__ == "__main__":
    asyncio.run(main())