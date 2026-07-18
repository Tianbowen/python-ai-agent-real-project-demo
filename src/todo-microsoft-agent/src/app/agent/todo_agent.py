# agent/todo_agent.py

import os

from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

from app.agent.tools import complete_todo, create_todo, delete_todo, update_todo, list_todos

def build_todo_agent() -> Agent:
    load_dotenv()

    client = OpenAIChatCompletionClient(
        api_key=os.environ['OPENAI_API_KEY'],
        base_url=os.environ['OPENAI_BASE_URL'],
        model=os.environ['OPENAI_CHAT_COMPLETION_MODEL'],
    )

    return Agent(
        client=client,
        name="TodoAssistant",
        description="使用自然语言管理待办事项",
        instructions=(
            "你是一名待办事项助手。"
            "创建任务时调用 create_todo。"
            "查询任务时调用 list_todos。"
            "完成任务时调用 complete_todo。"
            "修改任务时调用 update_todo。"
            "删除任务时调用 delete_todo。"
            "如果不知道待办ID，必须先调用list_todos查询。"
            "用户说今天、明天或后天时，将相对日期原样传给工具。"
            "不能编造工具结果，也不能绕过删除审批。"
            "始终使用简体中文。"
        ),
        tools=[
            create_todo,
            list_todos,
            complete_todo,
            update_todo,
            delete_todo,
        ],
    )

