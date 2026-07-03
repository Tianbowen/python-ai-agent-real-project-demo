# agents/get_other.py
# 最小业务工具：通用问答

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_TOKENS, logger

SYSTEM_PROMPT = """你是一名日程智慧服务助手，帮助梳理操作日常相关问题。

职责：
- 回答日程列表，添加，更新，提醒等日程相关问题

要求：
- 回答简洁，友好
- 回答控制在200字以内
- 格式要求美观，比如：列表输出表格，类别或优先级用emoji等。
"""

class GetOtherTool(AbstractTool):
    """通用问题工具：处理所有无法匹配到专项工具的问题"""
    
    name: str = "get_other"
    description = "通用日程查询，添加日程，更新日程，删除日程，到期前提醒等通用问题"

    def __init__(self, handler = None):
        super().__init__(handler=handler)
        self._llm = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            streaming=True # 开启流式输出
        )

    async def arun(self, query, **kwargs) -> str:
        history = self.context.chat_history.messages

        # 构建 Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{query}")
        ])

        chain = prompt | self._llm

        # 流式生成：每个token推送到StreamCallbackHandler
        full_text = ""
        try:
            async for chunk in chain.astream({
                "history": history,
                "query": query
            }):
                token = chunk.content
                if token:
                    full_text += token
                    await self.handler.put_token(token=token)
        except Exception as e:
            logger.error(f"GetOtherTool LLM 调用失败:{e}")
            error_msg = "抱歉，服务暂时出现问题，请稍后再试"
            await self.handler.put_token(error_msg)
            full_text = error_msg

        # 记录完整输出(供后处理使用)
        self.context.set_result_llm(full_text)

        # 推送业务结构化数据 (type=0 标识纯文本回答)
        await self.handler.put_data(
            biz_code=self.context.request_info.biz_code(),
            answer=full_text,
        )

        return "[GetOtherTool done]"

        