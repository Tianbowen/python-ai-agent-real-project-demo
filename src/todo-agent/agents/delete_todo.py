# agents/delete_todo.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, logger
from db.todo_db import todo_db

class DeleteTodoTool(AbstractTool):

    name = "delete_todo"
    description = "删除某个待办事项，需要从用户输入中提取任务标题关键词"

    def __init__(self, handler = None):
        super().__init__(handler)
        self._llm_sync = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0,
            max_tokens=32,
        )
        self._llm_stream = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0.7,
            max_tokens=80,
            streaming=True,
        )

    async def arun(self, query: str, **kwargs) -> None:
        keyword = await self._extract_keyword(query)
        item = todo_db.delete(keyword)

        if item:
            full_text = ""
            async for chunk in self._gen_success(item):
                token = chunk.content
                if token:
                    full_text += token
                    await self.handler.put_token(token=token)
            self.context.set_result_llm(full_text)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=full_text,
                data=[{"标题": item.title, "状态": "已删除"}],
            )
        else:
            full_text = ""
            async for chunk in self._gen_not_found(keyword):
                token = chunk.content
                if token:
                    full_text += token
                    await self.handler.put_token(token=token)
            self.context.set_result_llm(full_text)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=full_text,
                data=[],
            )
    
    async def _extract_keyword(self, query: str) -> str:
        prompt = ChatPromptTemplate.from_template(
            "从下面的用户输入中提取想要删除的任务关键词，"
            "只输出关键词本身，不超过10字，不要有任何解释：\n{query}"
        )

        resp = await (prompt | self._llm_sync).ainvoke({"query": query})
        keyword = resp.content.strip()
        return keyword if keyword else query[:10]
    
    def _gen_success(self, item):
        prompt = ChatPromptTemplate.from_template(
            "用简洁友好的语气告诉用户：待办「{title}」已成功删除，一句话，不超过30字。"
        )
        return (prompt | self._llm_stream).astream({"title": item.title})
    
    def _gen_not_found(self, keyword: str):
        prompt = ChatPromptTemplate.from_template(
            "用简洁友好的语气告诉用户：没有找到包含「{keyword}」的待办，"
            "建议先查看列表确认名称，一句话，不超过40字。"
        )
        return (prompt | self._llm_stream).astream({"keyword": keyword})