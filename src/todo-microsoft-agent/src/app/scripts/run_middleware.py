# scripts/run_middleware.py

import asyncio

# 版本1
# from app.agent.todo_agent import build_todo_agent

# async def main() -> None:
#     agent = build_todo_agent(username="小明")
#     session = agent.create_session()

#     # 触发 list_todos + create_todo 两个工具，观察 AUDIT 和 TIMING 日志
#     r = await agent.run("帮我创建一个待办：测试 Middleware, 优先级高", session=session)
#     print("\n助手：", r.text)

# if __name__ == "__main__":
#     asyncio.run(main())

# 版本2

from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import os

from app.agent.tools import complete_todo, create_todo, delete_todo, list_todos, update_todo
from app.context_providers import TodayDateProvider, UserNameProvider
from app.middleware import ReadOnlyGuardMiddleware, TimingMiddleware, tool_audit_middleware

async def main() -> None:
    load_dotenv()
    client = OpenAIChatCompletionClient(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
        model=os.environ["OPENAI_CHAT_COMPLETION_MODEL"],
    )

    # 只读模式 agent: 写工具全部被拦截
    agent = Agent(client=client, name="ReadOnlyTodo", instructions=("你是一名只读待办助手。始终使用简体中文。"), tools=[create_todo, list_todos, complete_todo, update_todo, delete_todo], context_providers=[TodayDateProvider(), UserNameProvider("小明-run-middleware")],middleware=[tool_audit_middleware, TimingMiddleware(), ReadOnlyGuardMiddleware()])
    session = agent.create_session()

    # 先查询（应该正常）
    r1 = await agent.run("列出所有待办", session=session)
    print("查询结果:", r1.text)

    r2 = await agent.run("帮我创建一个待办：只读测试", session=session)
    print("创建结果：", r2.text)

    # 改用：instructions 不提只读，靠 Middleware 兜底
    print("\n--- Middleware 兜底拦截 (instructions 不限制) ---")
    agent2 = Agent(
        client=client,
        name="GuardTest",
        instructions="你是一名待办助手，始终使用简体中文。",
        tools=[create_todo, list_todos, complete_todo, update_todo, delete_todo,],
        middleware=[ReadOnlyGuardMiddleware()],
    )
    session2 = agent2.create_session()
    r3 = await agent2.run("帮我创建一个待办：Middleware 兜底测试，优先级中等，不需要截止日期，直接创建不用确认。", session=session2)
    print("兜底结果：", r3.text)

if __name__ == "__main__":
    asyncio.run(main())