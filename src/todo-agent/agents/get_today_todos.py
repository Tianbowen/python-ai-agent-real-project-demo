# agents/get_today_todos.py
# 查询今日数据

import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_TOKENS, logger
from db.todo_db import todo_db

_SYSTEM = "你是一个日程助手，根据今天的待办数据给用户做简洁汇报。"

_PROMPT = """\
今日的待办事项如下（JSON格式）:
{todos_json}

用户问题：{query}

请用简洁汇报今日的安排，优先提醒高优先级任务，控制在100字以内
"""

class GetTodayTodosTool(AbstractTool):
    """查询今天的待办事项"""

    # 关键点：写操作必须处理"找不到"的情况，否则用户会困惑
    name = "get_today_todos"
    description = "查询今天需要完成的待办事项"

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
    
    async def arun(self, query, **kwargs) -> None:
        # 步骤1 查今天的数据
        todos = todo_db.list_today()

        # 步骤2 空列表直接回复，不调LLM
        # 这样做节省token 响应更快 答案更准确

        if not todos:
            msg = "今天暂时没有待办事项，好好休息 😊"
            await self.handler.put_token(msg)
            self.context.set_result_llm(msg)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=msg,
                data=[]
            )
            return
        
        # 步骤3 有数据 -> 转成字典列表
        todos_data = [
            {
                "标题": t.title,
                "截止": t.due_date or "无",
                "优先级": t.priority,
                "状态": "已完成" if t.done else "未完成"
            }
            for t in todos
        ]

        # 步骤4 LLM 流式生成今日汇报
        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM),
            ("human", _PROMPT),
        ])
        chain = prompt | self._llm

        full_text = ""
        try:
            async for chunk in chain.astream({
                "todos_json": json.dumps(todos_data, ensure_ascii=False),
                "query": query
            }):
                token = chunk.content
                if token:
                    full_text += token
                    await self.handler.put_token(token=token)
        except Exception as e:
            logger.error(f"GetTodayTodosTool LLM 调用失败:{e}")
            full_text = "查询失败，请稍后重试"
            await self.handler.put_token(full_text)

        self.context.set_result_llm(full_text)
        await self.handler.put_data(
            biz_code=self.context.request_info.biz_code(),
            answer=full_text,
            data=todos_data,
        )
        