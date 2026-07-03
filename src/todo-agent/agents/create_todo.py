# agents/create_todo.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_MAX_TOKENS
from db.todo_db import todo_db

from datetime import datetime
from typing import Optional

class CreateTodoTool(AbstractTool):
    """创建一条新的待办事项"""

    name = "create_todo"
    description = "创建新的待办事项，需要标题，可选截止时间和优先级"

    def __init__(self, handler = None):
        super().__init__(handler)
        # 流式 LLM：用于生成确认语
        self._llm_stream = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0.7,
            max_tokens=100,
            streaming=True,
        )
        # 同步 LLM：用于提取标题（只需要短文本，不需要流式）
        self._llm_sync = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0,
            max_tokens=32,
        )

    async def arun(self, query: str, **kwargs) -> None:
        title = None
        if self.context.ctx:
            title = self.context.ctx.slot_value("title")
        
        if not title:
            title = await self._extract_title(query)

        due_date = self.context.ctx.slot_value("due_date") if self.context.ctx else None
        if not due_date:
            due_date = await self._extract_due_date(query=query)

        priority = self.context.ctx.slot_value("priority") if self.context.ctx else "中"

        item = todo_db.create(
            title= title,
            due_date= due_date,
            priority= priority
        )

        full_text = ""
        async for chunk in self._gen_confirm(item):
            token = chunk.content
            if token:
                full_text += token
                await self.handler.put_token(token)

        self.context.set_result_llm(full_text)
        await self.handler.put_data(
            tool_name=self.context.request_info.biz_code(),
            answer=full_text,
            data=[{
                "id": item.id,
                "标题": item.title,
                "截止": item.due_date or "无",
                "优先级": item.priority,
                "状态": "未完成",
            }]
        )

    async def _extract_title(self, query: str) -> str:
        """
        用LLM从用户输入里提取任务标题
        为什么用同步invoke 而是不是 astream
        这里只需要一个短结果，而不需要流式推送给用户
        """
        prompt = ChatPromptTemplate.from_template(
            "从下面的用户输入中提取任务标题，"
            "只输出标题本身，不超过20字，不要加任何解释：\n{query}"
        )
        resp = (prompt | self._llm_sync).invoke({"query": query})
        title = resp.content.strip()
        # 兜底： LLM提取失败时，直接用用户输入的前20字
        return title if title else query[:20]
    
    async def _extract_due_date(self, query: str) -> Optional[str]:
        """
        从用户输入提取截止日趋，输出 YYYY-MM-DD 或 YYYY-MM-DD HH:MM 格式
        提取不到返回 None
        """
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = ChatPromptTemplate.from_template(
            "今天是{today}。"
            "从下面的用户输入中提取截止日期/时间，"
            "输出格式为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM"
            "如果没有提到日期则只输出 null, 不要输出任何其他内容:\n{query}"
        )
        resp = (prompt | self._llm_sync).invoke({"today": today, "query": query})
        result = resp.content.strip()
        return None if result.lower() == "null" else result
    
    def _gen_confirm(self, item):
        """
        生成创建成功的确认语(流式)
        返回的是 astream 迭代器，在arun 里用 async for 消费
        """
        extra_parts = []
        if item.due_date:
            extra_parts.append(f"截止时间：{item.due_date}")
        if item.priority:
            extra_parts.append(f"优先级：{item.priority}")
        extra = ",".join(extra_parts)

        prompt = ChatPromptTemplate.from_template(
            "用友好简洁的语气告诉用户：已成功创建待办「{title}」{extra}。"
            "一句话即可，结尾加个 ✓，不超过50字。"
        )
        return (prompt | self._llm_stream).astream({
            "title": item.title,
            "extra": f"({extra})" if extra else "",
        })
