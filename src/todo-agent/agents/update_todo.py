# agents/update_todo.py

# 第一版 
# import json
# import re
# 第二版
from pydantic import BaseModel, Field # Pydantic v2, LangChain 内置依赖
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, logger
from db.todo_db import todo_db

# 第二版 - 定义数据模型
class UpdateParams(BaseModel):
    """LLM提取的更新参数，字段与 tasks.yaml slots 对应"""
    title: str = Field(description="要修改的原任务关键词")
    new_title: Optional[str] = Field(None, description="新标题")
    new_due_date: Optional[str] = Field(None, description="新截止日期，格式 YYYY-MM-DD")
    new_priority: Optional[str] = Field(None, description="新优先级: 高/中/低")

class UpdateTodoTool(AbstractTool):
    """"""
    
    name = "update_todo"
    description = "更新某个待办事项的标题，截止日期或优先级"

    def __init__(self, handler = None):
        super().__init__(handler)
        # self._llm_sync = ChatOpenAI(
        #     base_url=LLM_API_BASE,
        #     api_key=LLM_API_KEY,
        #     model=LLM_MODEL_NAME,
        #     temperature=0,
        #     max_tokens=128,
        # )
        # with_structured_output: 绑定 Pydantic 模型，LLM输出直接映射成对象
        self._llm_structured_output = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0,
            max_tokens=256,
        ).with_structured_output(UpdateParams) # <- 关键

        self._llm_stream = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0.7,
            max_tokens=80,
            streaming=True,
        )

    async def arun(self, query: str, **kwargs) -> None:
        params = await self._extract_params(query)        

        # 第一版
        # keyword = params.get("title", query[:10])
        # item = todo_db.update(
        #     title_keyword=keyword,
        #     new_title=params.get("new_title"),
        #     new_due_date=params.get("new_due_date"),
        #     new_priority=params.get("new_priority"),
        # )

        # 第二版
        keyword = params.title
        item = todo_db.update(
            title_keyword=keyword,
            new_title=params.new_title,
            new_due_date=params.new_due_date,
            new_priority=params.new_priority,
        )

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
                data=[{"标题": item.title, "截止": item.due_date or "无", "优先级": item.priority}],
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
                answer=full_text, data=[]
            )
    # 第一版
    # async def _extract_params(self, query: str) -> dict:
    #     """让 LLM 把用户输入解析成结构化 JSON, 再用 re.search 提取"""
    #     prompt = ChatPromptTemplate.from_template(
    #         "从用户输入中提取任务更新信息，以JSON格式输出，可用字段：\n"
    #         "- title: 要修改的原任务关键词（必填） \n"
    #         "- new_title: 新标题（可选）\n"
    #         "- new_due_date: 新截止日期 YYYY-MM-DD (可选) \n"
    #         "- new_priority: 新优先级 高/中/低 (可选) \n"
    #         "只输出JSON,不要有其他文字。\n用户输入:{query}"
    #     )
    #     resp = await (prompt | self._llm_sync).ainvoke({"query": query})
    #     text = resp.content.strip()
    #     try:
    #         json_match = re.search(r'\{.*\}', text, re.DOTALL)
    #         if json_match:
    #             return json.loads(json_match.group())
    #     except Exception as e:
    #         logger.warning(f"[UpdateTodo] JSON 解析失败：{text}")
    #     return {"title": query[:10]}

    # 第二版
    async def _extract_params(self, query: str) -> UpdateParams:
        """
        用 structured output 代替 regex + json.loads
        LLM直接返回 UpdateParams 对象，字段自动校验
        """
        prompt= ChatPromptTemplate.from_template(
            "从用户输入中提取任务更新信息。\n用户输入:{query}"
        )
        # 注意：chain 末尾不再需要JsonOutputParser, 模型自动处理
        chain = prompt | self._llm_structured_output
        return await chain.ainvoke({"query": query})
    
    def _gen_success(self, item):
        prompt = ChatPromptTemplate.from_template(
            "用简洁友好的语气告诉用户：待办「{title}」已成功更新，一句话，不超过30字。"
        )
        return (prompt | self._llm_stream).astream({"title": item.title})
    
    def _gen_not_found(self, keyword: str):
        prompt = ChatPromptTemplate.from_template(
            "用简洁友好的语气告诉用户：没有找到包含「{keyword}」的待办，"
            "建议先查看列表确认名称，一句话，不超过40字。"
        )
        return (prompt | self._llm_stream).astream({"keyword": keyword})


        
    