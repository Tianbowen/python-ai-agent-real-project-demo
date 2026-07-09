# agents/smart_todo.py
# 模式三：条件分支编排

# 场景：用户说"帮我完成开会，没有就帮我创建"
# 执行顺序：
# 查找开会
#     |-> 找到了 -> 标记完成 -> 告知成功
#     |-> 没找到 -> 创建任务 -> 告知已创建

# 核心python知识： if/else + 不同分支调用不同逻辑

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, logger
from db.todo_db import todo_db

class SmartTodoTool(AbstractTool):
    """
    条件分支编排示例：智能完成/创建任务

    执行逻辑：
    IF 数据库里找到了对应任务
        THEN 标记完成
    ELSE
        THEN 自动创建这个任务

    关键点：分支由数据决定，不同分支走完全不同的路
    """

    name = "smart_todo"
    description = "智能处理任务：找到则完成，找不到则创建"

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
        # 前置步骤：提取关键词(条件判断的依据)
        keyword = await self._extract_keyword(query=query)

        # 条件判断：在DB里找
        existing = self._find_todo(keyword=keyword)

        if existing and not existing.done:
            # 分支A 找到了且未完成 -> 完成它
            todo_db.complete(keyword)

            full_text = ""
            async for chunk in self._gen_complete_msg(existing.title):
                token = chunk.context
                if token:
                    full_text += token
                    await self.handler.put_token(token=token)

            self.context.set_result_llm(full_text)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=full_text,
                data=[{"标题": existing.title, "状态": "已完成"}]
            )
        elif existing and existing.done:
            # 分支B 找到了但已经完成了
            msg = f"「{existing.title}」已经是完成状态了 ✅"
            await self.handler.put_token(msg)
            self.context.set_result_llm(msg)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=msg,
                data=[],
            )
        else:
            # 分支C 没找到 -> 创建它
            new_item = todo_db.create(title=keyword)

            full_text = ""
            async for chunk in self._gen_create_msg(new_item.title):
                token = chunk.content
                if token:
                    full_text += token
                    await self.handler.put_token(token=token)
            
            self.context.set_result_llm(full_text)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=full_text,
                data=[{"标题": new_item.title, "状态": "未完成"}]
            )
        
    # 工具方法
    def _find_todo(self, keyword: str):
        """在DB里查找包含关键词的任务"""
        for item in todo_db.list_all():
            if keyword in item.title:
                return item
        return None
    
    async def _extract_keyword(self, query: str) -> str:
        prompt = ChatPromptTemplate.from_template(
            "从用户输入中提取任务关键词，只输出关键词，不超过10字: \n{query}"
        )
        resp = await (prompt | self._llm_sync).ainvoke({"query": query})
        return resp.content.strip() or query[:10]
    
    def _gen_complete_msg(self, title: str):
        prompt = ChatPromptTemplate.from_template(
            "简洁告诉用户「{title}」已标记完成 ✅，一句话。"
        )
        resp = (prompt | self._llm_stream).astream({"title": title})

    def _gen_create_msg(self, title: str):
        prompt = ChatPromptTemplate.from_template(
            "简洁告诉用户：没有找到该任务，已自动创建「{title}」📝，一句话。"
        )
        return (prompt | self._llm_stream).astream({"title": title})