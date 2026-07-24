# scripts/run_mcp_client.py
"""
用 MCPStdioTool 连接到 todo-mcp server, 验证工具可被外部调用
"""

import asyncio
import os
import sys

from agent_framework import Agent, MCPStdioTool
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

async def main() -> None:
    load_dotenv()
    client = OpenAIChatCompletionClient(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
        model=os.environ["OPENAI_CHAT_COMPLETION_MODEL"],
    )

    # 用 uv run 启动 MCP Server 子进程
    mcp_tool = MCPStdioTool(
        name="todo-mcp",
        command="uv", # 当前 python 解释器
        args=["run", "python", "-m", "app.mcp_server"], # 启动 Server 模块
        description="Todo 待办事项管理工具集",
    )

    async with mcp_tool:
        # 查看 Server 暴露了哪些工具
        tool_names = [t.name for t in mcp_tool.functions]
        print("MCP Server 暴露的工具：", tool_names)

        # 用这些工具创建一个 Agent(消费者)
        consumer_agent = Agent(
            client=client,
            name="MCPConsumer",
            instructions="你是一名待办助手，使用MCP工具管理任务。始终使用简体中文。",
            tools=mcp_tool,
        )
        session = consumer_agent.create_session()

        r = await consumer_agent.run(
            "帮我创建一个待办：体验 MCP 工具，优先级高",
            session = session,
        )
        print("助手：", r.text)

if __name__ == "__main__":
    asyncio.run(main())