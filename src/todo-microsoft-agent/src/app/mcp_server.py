# app/mcp_server.py(MCP Server入口)
"""
把TodoAgent的工具暴露为 MCP Server (stdio 传输)
运行方式：uv run python -m app.mcp_server
"""

import asyncio
import os

from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework import Agent
from dotenv import load_dotenv
from mcp.server.stdio import stdio_server

from app.agent.tools import complete_todo, create_todo, delete_todo, list_todos, update_todo
from app.context_providers import TodayDateProvider

def build_map_agent() -> Agent:
    load_dotenv()
    client = OpenAIChatCompletionClient(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
        model=os.environ["OPENAI_CHAT_COMPLETION_MODEL"],
    )
    return Agent(
        client=client,
        name="TodoMCPAgent",
        instructions=(
            "你是一名待办事项助手，通过MCP协议提供工具。始终使用简体中文。"
        ),
        tools=[create_todo, list_todos, complete_todo, update_todo, delete_todo],
        context_providers=[TodayDateProvider()],
    )

async def main() -> None:
    agent = build_map_agent()
    mcp_server = agent.as_mcp_server(server_name="todo-mcp")

    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())