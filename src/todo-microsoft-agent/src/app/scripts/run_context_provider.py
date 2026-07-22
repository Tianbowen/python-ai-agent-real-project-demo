# scripts/run_context_provider.py

import asyncio

from agent_framework import AgentSession

from app.agent.todo_agent import build_todo_agent

async def main() -> None:
    agent = build_todo_agent(username="小明")
    session = agent.create_session()

    # 直接问今天是几号，模型应能正确回答(靠 TodayDateProvider 注入)
    r1 = await agent.run("你好，今天是几号", session=session)
    print("回答：", r1.text)

    # 问候时应称呼用户名（靠 UserNameProvider 注入）
    r2 = await agent.run("帮我创建一个今天到期的待办：复习 ContextProvider", session=session)
    print("创建待办:", r2.text)

if __name__ == "__main__":
    asyncio.run(main())