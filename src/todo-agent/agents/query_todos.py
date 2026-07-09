# agents/query_todos.py

import json
import re
from datetime import datetime, timedelta

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_TOKENS, logger
from db.todo_db import todo_db

class QueryTodosTool(AbstractTool):
    """按日期，优先级，状态条件查询待办"""

    name = "query_todos"
    description = "按日期，优先级，完成状态筛选待办事项"

    def __init__(self, handler = None):
        super().__init__(handler)
        self._llm_sync = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0,
            max_tokens=128,
        )
        self._llm_stream = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            streaming=True,
        )

    async def arun(self, query: str, **kwargs) -> None:
        # 步骤1 LLM 提取查询条件
        params = await self._extract_params(query)
        date_str = params.get("date")
        priority = params.get("priority")
        status = params.get("status")
        label = params.get("label") # 给回复用的自然语言描述，如"明天"

        # 按条件查询
        todos = todo_db.query(date_str=date_str, priority=priority, status=status)

        # 无结果直接返回
        if not todos:
            condition = label or date_str or priority or status or "该条件"
            msg = f"「{condition}」下暂无符合条件的待办事项"
            await self.handler.put_token(msg)
            self.context.set_result_llm(msg)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=msg, data=[]
            )
            return
        
        # 如果有结果 -> LLM流式汇报
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
            ("system", "你是一个日程助手，根据待办数据给用户做简洁汇报"),
            ("human", 
             "{label}的待办事项如下（JSON格式）：\n{todos_json}\n\n"
             "用户问题：{query}\n\n"
             "请简洁汇报，优先提醒高优先级任务，控制在100字以内。")
        ])

        full_text = ""
        async for chunk in (prompt | self._llm_stream).astream({
            "label": label or "查询结果",
            "todos_json": json.dumps(todos_data, ensure_ascii=False),
            "query": query,
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

    async def _extract_params(self, query: str) -> dict:
        """
        用LLM把自然语言转成结构化查询条件
        返回{"date": "YYYY-MM-DD", "priority": "高", "status": "未完成", "label": "明天"}
        所有字段均可为null
        """

        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        prompt = ChatPromptTemplate.from_template(
            "今天是{today}, 明天是{tomorrow}。\n"
            "从用户输入中提取查询条件，输出JSON,可用字段：\n"
            "- date: 目标日期 YYYY-MM-DD (可选)\n"
            "- priority: 优先级　高/中/低 (可选)\n"
            "- status: 完成状态 未完成/已完成 (可选)\n"
            "- label: 日期的自然语言描述，如「明天」「后天」「7月10日」（可选）\n"
            "只输出JSON，不要其他文字。\n"
            "用户输入：{query}"
        )
        resp = await (prompt | self._llm_sync).ainvoke({
            "today": today, "tomorrow": tomorrow, "query": query,
        })
        try:
            m = re.search(r'\{.*\}', resp.content.strip(), re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception as e:
            logger.warning(f"[QueryTodos] 条件提取失败:{resp.content}")
        return {}