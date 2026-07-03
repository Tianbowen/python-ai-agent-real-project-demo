# agents/get_todos.py

import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_TOKENS
from db.todo_db import todo_db

# 系统角色：告诉LLM它的职责
_SYSTEM = "你是一个友好的日程助手，请根据提供的待办数据，用自然语言给用户做简洁的总结。"

# 用户 Prompt: 把结构化数据 + 用户问题传给 LLM
_PROMPT = """\
用户的待办事项列表如下（JSON格式）：
{todos_json}

用户问题：{query}

请用简洁友好的语言总结，突出重要/紧急的任务，控制在150字以内。
"""

class GetTodosTool(AbstractTool):
    """查询用户所有待办，并用LLM生成自然语言摘要"""

    name = "get_todos"
    description = "查询用户所有待办事项"

    def __init__(self, handler = None):
        super().__init__(handler)
        self._llm = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            streaming=True,
        )

    async def arun(self, query: str, **kwargs) -> None:
        todos = todo_db.list_all()

        todos_data = [
            {
                "标题": t.title,
                "截止": t.due_date or "无",
                "优先级": t.priority,
                "状态": "已完成" if t.done else "未完成",
            }
            for t in todos
        ]

        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM),
            ("human", _PROMPT),
        ])

        chain = prompt | self._llm

        full_text = ""
        async for chunk in chain.astream({
            "todos_json": json.dumps(todos_data, ensure_ascii=False),
            "query": query
        }):
            token = chunk.content
            if token:
                full_text += token
                await self.handler.put_token(token=token)

        self.context.set_result_llm(full_text)

        await self.handler.put_data(
            biz_code=self.context.request_info.biz_code(),
            answer=full_text,
            data=todos_data,
        )

