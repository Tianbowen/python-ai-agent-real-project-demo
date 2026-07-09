# agent/tool_agent.py
# 演示：用@tool + bind_tools 替代手写 Prompt 提取参数的方式

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, logger
from db.todo_db import todo_db

# 1. 用@tool 声明工具函数
# LangChain 会把函数签名和 docstring 自动转成 LLM 能理解的 schema
# LLM 看到这些定义后，会在合适时机自动选择调用哪个

@tool
def tool_delete_todo(title_keyword: str) -> str:
    """删除标题中包含关键词的待办事项，返回操作结果"""
    item = todo_db.delete(title_keyword)
    return f"已删除「{item.title}」" if item else f"未找到包含「{title_keyword}」的待办"

@tool
def tool_update_todo(
    title_keyword: str,
    new_title: str = None,
    new_due_date: str = None,
    new_priority: str = None,
) -> str:
    """更新待办事项，可修改标题、截止日期（YYYY-MM-DD）、优先级（高/中/低）"""
    item = todo_db.update(title_keyword, new_title, new_due_date, new_priority)
    return f"已更新「{item.title}」" if item else f"未找到包含「{title_keyword}」的待办"

@tool
def tool_query_todos(
    date: str = None,
    priority: str = None,
    status: str = None,
) -> str:
    """按条件查询待办：date 格式 YYYY-MM-DD，priority 高/中/低，status 未完成/已完成"""
    items = todo_db.query(date_str=date, priority=priority, status=status)
    if not items:
        return "没有符合条件的待办事项"
    return "\n".join([f"- {t.title}（{t.due_date or '无截止'}，{t.priority}）" for t in items])

# 2. 工具列表
_TOOLS = [tool_delete_todo, tool_update_todo, tool_query_todos]

# 工具名 -> 函数 的映射（执行时用）
_TOOL_MAP = {t.name: t for t in _TOOLS}

class ToolAgentTool(AbstractTool):
    """
    使用 Function Calling 的 Agent:
    LLM  自动决定调用哪个工具，传什么参数，无需手写参数提取 Prompt
    """

    name = "tool_agent"
    description = "通用 Function Calling Agent, 支持删除/更新/条件查询"

    def __init__(self, handler = None):
        super().__init__(handler)

        # 3. bind_tools：把工具 schema 注入LLM
        self._llm = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0
        ).bind_tools(_TOOLS)

        # 生成最终回复用的普通流式 LLM（不带工具）
        self._llm_stream = ChatOpenAI(
            base_url=LLM_API_BASE, api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME, temperature=0.7,
            max_tokens=150, streaming=True,
        )

    async def arun(self, query: str, **kwargs) -> None:
        messages = [HumanMessage(content=query)]

        # 4. ReAct 循环：最多执行 3轮工具调用
        for _ in range(len(_TOOLS)):
            response = await self._llm.ainvoke(messages)
            messages.append(response)

            # 没有 tool_call -> LLM 已给出最终答案，退出循环
            if not response.tool_calls:
                break

            # 有 tool_call -> 逐个执行工具，把结果喂回 LLM
            for tc in response.tool_calls:
                tool_fn = _TOOL_MAP.get(tc["name"])
                if tool_fn is None:
                    result = f"未知工具:{tc['name']}"
                else:
                    # 执行工具函数，args 由LLM 自动填充
                    result = tool_fn.invoke(tc["args"])
                    logger.info(f"[ToolAgent] 调用 {tc['name']}({tc['args']}) -> {result}")

                # 5. ToolMessage: 把工具执行结果返回给LLM
                messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tc["id"],
                ))
        
        # 6. 流式输出最终回复
        # 此时 messages[-1] 是 LLM 的最终 AIMessage
        final_answer = messages[-1].content if messages else "处理完成"

        # 如果最后一条已经是文字回复，直接流式推送
        full_text = ""
        async for chunk in self._llm_stream.astream(
            f"用简洁友好的语气把以下操作结果告诉用户：{final_answer}"
        ):
            token = chunk.content
            if token:
                full_text += token
                await self.handler.put_token(token)
        self.context.set_result_llm(full_text)
        await self.handler.put_data(
            biz_code=self.context.request_info.biz_code(),
            answer=full_text, data=[],
        )
