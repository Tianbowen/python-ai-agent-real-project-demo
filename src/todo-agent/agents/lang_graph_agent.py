# agent/lang_graph_agent.py
# LangGraph 实现多步骤推理 Agent

from datetime import datetime
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, logger
from db.todo_db import todo_db

# 1. 工具定义
#    @tool 把函数签名 + docstring 转成 LLM 能理解的 schema
#    LangGraph 的 ToolNode 会自动解析并执行这些函数

@tool
def lg_get_all_todos() -> str:
    """获取所有待办事项列表"""
    items = todo_db.list_all()
    if not items:
        return "当前没有任何待办事项"
    return "\n".join([
        f"- {t.title} (截止:{t.due_date or '无'}, {t.priority}优先级, {'已完成' if t.done else '未完成' })"
        for t in items
    ])

@tool
def lg_query_todos(date: str = None, priority: str = None, status: str = None) -> str:
    """
    按条件查询待办事项
    date: 日期 YYYY-MM-DD (可选)
    priority: 优先级 高/中/低 (可选)
    status: 未完成/已完成 (可选)
    """
    items = todo_db.query(date_str=date, priority=priority, status=status)
    if not items:
        return "没有符合条件的待办事项"
    return "\n".join([
        f"- {t.title}（截止:{t.due_date or '无'}，{t.priority}，{'已完成' if t.done else '未完成'}）"
        for t in items
    ])

@tool
def lg_create_todo(title: str, due_date: str = None, priority: str = "中") -> str:
    """
    创建新待办事项
    title: 任务标题
    due_date: 截止日期 YYYY-MM-DD 或 YYYY-MM-DD HH:MM (可选)
    priority: 高/中/低 (默认中)
    """

@tool
def lg_update_todo(
    title_keyword: str, 
    new_title: str = None,
    new_due_date: str = None,
    new_priority: str = None,
) -> str:
    """
    更新待办事项
    title_keyword: 要修改的任务标题关键词
    new_due_date: 新截止日期 YYYY-MM-DD (可选)
    new_priority: 新优先级 高/中/低 (可选)
    """
    item = todo_db.update(title_keyword=title_keyword, new_due_date=new_due_date, new_priority=new_priority)
    return f"已更新「{item.title}」" if item else f"未找到包含「{title_keyword}」的待办"

@tool
def lg_delete_todo(title_keyword: str) -> str:
    """删除标题中包含关键词的待办事项"""
    item = todo_db.delete(title_keyword=title_keyword)
    return f"已删除「{item.title}」" if item else f"未找到包含「{title_keyword}」的待办"

@tool
def lg_complete_todo(title_keyword: str) -> str:
    """将标题包含关键词的待办标记为已完成"""
    item = todo_db.complete(title_keyword=title_keyword)
    return f"「{item.title}」已完成 ✅" if item else f"未找到包含「{title_keyword}」的待办"

_TOOLS = [
    lg_get_all_todos,
    lg_query_todos,
    lg_create_todo,
    lg_update_todo,
    lg_delete_todo,
    lg_complete_todo,
]

# 2. State 定义
#    TypedDict 描述图的共享状态结构
#    add_messages 是 LangGraph 内置 reducer：
#      - 普通赋值会「覆盖」字段
#      - add_messages 会「追加」消息列表，保留完整对话历史

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# 3. 图构建

def build_graph(llm):
    """
    构建并编译 LangGraph 图

    节点：
        llm_node -- 调用 LLM, LLM 可能输出文字或 tool_calls
        tool_node -- LangGraph 内置, 自动执行 tool_calls 里的工具

    边：
        START -> llm_node
        llm_node -> tool_node (当 LLM 输出了 tool_calls)
        llm_node -> END       (当 LLM 输出了文字， 无 tool_calls)
        tool_node -> llm_node (工具结果回传给 LLM 继续推理)
    """

    # Node 1: LLM 推理
    def llm_node(state: AgentState) -> dict:
        """
        读取 state.messages, 调用 LLM
        LLM 返回 AIMessage, 可能包含 tool_calls 或纯文字内容
        返回的字典由 add_messages reducer 追加到 state.messages
        """
        response = llm.invoke(state["messages"])
        return {"messages": [response]}
    
    # Node 2: 工具执行 (内置)
    # ToolNode 自动：
    #   1. 从最新 AIMessage 里取出 tool_calls
    #   2. 按名称找到对应 @tool 函数并执行
    #   3. 把结果包装成 ToolMessage 追加到 messages
    tool_node = ToolNode(_TOOLS)

    # 建图
    graph = StateGraph(AgentState)

    graph.add_node("llm_node", llm_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "llm_node")

    # 条件边：tools_condition 是 LangGraph 内置条件函数
    #   检查最新 AIMessage 是否有 tool_calls
    #   有 -> 路由到 "tools" (对应 tool_node)
    #   无 -> 路由到 END

    graph.add_conditional_edges("llm_node", tools_condition)


    # 工具执行完 -> 回到 LLM 继续推理 (形成循环)
    graph.add_edge("tools", "llm_node")

    # compile() 把图编译成可执行的 Runnable
    return graph.compile()

# 4. 工具类 (接入现有框架)

class LangGraphAgentTool(AbstractTool):
    """
    LangGraph 多步骤推理 Agent

    与 ToolAgentTool 的区别：
        ToolAgentTool -- 手写 for 循环控制 ReAct 流程
        LangGraphAgentTool -- 用图声明式定义，框架自动处理循环和路由
    """

    name = "lang_graph_agent"
    description = "多步骤推理 Agent, 适合需要连续调用多个工具的复合任务"

    def __init__(self, handler = None):
        super().__init__(handler)

        llm = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0,
        ).bind_tools(_TOOLS) # 把工具 schema 注入 LLM

        self._graph = build_graph(llm=llm)

    async def arun(self, query: str, **kwargs) -> None:
        today = datetime.now().strftime("%Y-%m-%d")

        initial_state = {
            "messages": [
                SystemMessage(content=(
                    f"你是一个智能日程助手，今天是{today}。\n"
                    "你可以调用工具查询、创建、更新、删除、完成待办事项。\n"
                    "遇到复合任务时，请按步骤依次调用工具，最后给出完整汇报。"
                )),
                HumanMessage(content=query)
            ]
        }

        # ainvoke：执行完整图，等所有节点跑完后返回最终 State
        # 图会自动处理 LLM -> 工具 -> LLM的循环，知道 LLM不再调用工具
        logger.info(f"[LangGraph] 开始执行，query={query}")
        final_state = await self._graph.ainvoke(initial_state)

        # 最后一条消息就是 LLM的最终回复
        final_message = final_state["messages"][-1]
        full_text = final_message.content or "任务已处理完成。"

        logger.info(f"[LangGraph] 执行完成，共{len(final_state['messages'])} 条消息")

        # 逐字符推送，模拟流式效果
        for char in full_text:
            await self.handler.put_token(char)
            
        self.context.set_result_llm(full_text)
        await self.handler.put_data(
            biz_code=self.context.request_info.biz_code(),
            answer=full_text,
            data=[],
        )