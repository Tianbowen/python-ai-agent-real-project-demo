# agents/complete_todo.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_MAX_TOKENS, logger
from db.todo_db import todo_db

class CompleteTodoTool(AbstractTool):
    """标记某个待办事项为已完成"""

    name = "complete_todo"
    description = "标记某个待办事项为已完成，需要从用户输入中提取任务标题"

    def __init__(self, handler = None):
        super().__init__(handler)
        # 同步 LLM:提取关键词，不需要流式
        self._llm_sync = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0,
            max_tokens=32,
        )
        # 流式 LLM: 生成确认或提示语
        self._llm_stream = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0.7,
            max_tokens=80,
            streaming=True,
        )

    async def arun(self, query: str, **kwargs) -> None:
        # 步骤1 从用户输入提取任务关键字
        keyword = await self._extract_keyword(query=query)
        # 步骤2 在数据库里查找并标记完成
        item = todo_db.complete(keyword)
        # 步骤3 根据结果生成不同的回复
        if item:
            # 找到并标记成功
            full_text = ""
            async for chunk in self._gen_success(item=item):
                token = chunk.content
                if token:
                    full_text += token
                    await self.handler.put_token(token=token)

            self.context.set_result_llm(full_text)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=full_text,
                data=[{
                    "标题":   item.title,
                    "截止":   item.due_date or "无",
                    "优先级": item.priority,
                    "状态":   "已完成",
                }]
            )
        else:
            # 找不到匹配的任务
            full_text = ""
            async for chunk in self._gen_not_found(keyword=keyword):
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
        """
        从给用户输入中提取任务关键词。
        用同步 invoke：只需要一个短结果，不用流式

        示例：
        "我完成了开会" -> "开会"
        "把买菜标记为完成" -> "买菜"
        "刚刚做完PR Review" -> "PR Review"
        """

        prompt = ChatPromptTemplate.from_template(
            "从下面的用户输入中提取想要标记为完成的任务关键词，"
            "只输出关键词本身，不超过10字，不要有任何解释：\n{query}"
        )

        resp = await (prompt | self._llm_sync).ainvoke({"query": query})
        keyword = resp.content.strip()
        # 兜底：提取失败就用用户输入的前10字
        return keyword if keyword else query[:10]
    
    def _gen_success(self, item):
        """生成完成成功的确认语（流式）"""
        prompt = ChatPromptTemplate.from_template(
            "用简洁友好的语气告诉用户：待办「{title}」已标记为完成✅，"
            "一句话即可，不超过30字。"
        )
        return (prompt | self._llm_stream).astream({"title": item.title})
    
    def _gen_not_found(self, keyword: str):
        """生成找不到任务的提示语（流式）"""
        prompt = ChatPromptTemplate.from_template(
            "用简洁友好的语气告诉用户：没有找到包含「{keyword}」的待办事项，"
            "建议用户先查看待办列表确认任务名称，一句话即可，不超过40字。"
        )
        return (prompt | self._llm_stream).astream({"keyword": keyword})
