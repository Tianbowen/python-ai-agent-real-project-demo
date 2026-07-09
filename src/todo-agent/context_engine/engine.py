# context_engine/engine.py

import json
import re
from typing import Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from cache.cache import get_session, set_session
from config import (LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, HISTORY_MAX, logger, load_tasks_yaml)

from models.ce_models import ConversationSession
from models.context_info import ContextInfo

# Prompt 模板

CLASSIFICATION_PROMPT = """你是一个日程服务意图分类器，根据用户的输入，从给定的主题和任务列表中选择最匹配的项。

可选主题和任务列表：
{topics_and_tasks}

对话历史摘要：{history_summary}
用户输入:{query}

请严格按照以下JSON格式输出，不要有任何多余的文字：
{{
    "topic_name": "选择的主题名称",
    "task_name": "选择的任务名称",
    "tool": "对应的工具名称"
}}

注意：只能从给定的选项中选择，如果不确定请选择[通用查询]下的[通用回答]。
"""

_CANCEL_WORDS = {"取消", "否", "不", "算了", "放弃", "不要", "别", "no"}
_CONFIRM_WORDS = {"确认", "是", "对", "好", "确定", "继续", "yes", "ok"}

class ContextManager:
    """
    上下文管理器：实现主题/任务识别 + 会话状态管理

    核心职责：
    1. 从缓存回复会话状态(ConversationSession)
    2. 用 LLM 识别(主题 -> 任务 -> 工具)
    3. 将识别结果写回 ContextInfo
    """

    def __init__(self):
        self._tasks_config = load_tasks_yaml()
        self._llm = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0, # 分类任务用 temperature=0, 要确定性输出
            max_tokens=256,
        )

    # 会话管理
    def get_or_create_session(self, context: ContextInfo) -> ConversationSession:
        """从缓存恢复会话，不存在则新建"""
        biz_code = context.request_info.biz_code()
        session_id = context.request_info.conversation_id()
        cache_key = f"{biz_code}:{session_id}"

        session = get_session(cache_key)
        if session is None:
            session = ConversationSession(
                user_id=biz_code,
                session_id=session_id
            )
            logger.info(f"新建会话:{cache_key}")
        else:
            logger.info(f"恢复会话:{cache_key}, topic={session.topic_name()}, task={session.task_name()}")

        context.ctx = session
        return session

    def save_session(self, context: ContextInfo):
        """将会话状态写回缓存"""
        if context.ctx is None:
            return
        biz_code = context.request_info.biz_code()
        session_id = context.request_info.conversation_id()
        cache_key = f"{biz_code}:{session_id}"
        set_session(cache_key, context.ctx)

    # 主题/任务识别

    def _build_topics_desc(self, biz_code: str) -> str:
        """从 tasks.yaml 构建供 LLM 分类用的主题/任务描述文本"""
        biz_config = self._tasks_config.get("biz_codes", {}).get(biz_code, {})
        topics = biz_config.get("topics", [])

        lines = []
        for topic in topics:
            lines.append(f"主题：{topic['name']}")
            if topic.get('description'):
                lines.append(f" 描述:{topic['description']}")
            for task in topic.get('tasks', []):
                lines.append(f" -   任务:{task['name']}, 工具: {task['tool']}")
                if task.get("description"):
                    lines.append(f"     说明：{task['description']}")
                # 新增：把examples 拼进入，帮 LLM 学会路由
                if task.get("examples"):
                    examples_str = "、".join(task["examples"])
                    lines.append(f"     示例：{examples_str}")
        return "\n".join(lines)

    def _build_history_summary(self, session: ConversationSession) -> str:
        """把最近几轮对话压缩成摘要文本，给分类LLM做上下文"""
        messages = session.get_recent_history(max_turns=3)
        if not messages:
            return "无历史对话"
        lines = []
        for msg in messages:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            # 只取前 100字，避免 token浪费
            content = str(msg.content)[:100]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _classify(self, query: str, biz_code: str, session: ConversationSession) -> Tuple[str, str, str]:
        """
        调用LLM识别主题/任务/工具
        返回(topic_name, task_name, tool_name)
        """
        topics_desc = self._build_topics_desc(biz_code)
        history_summary = self._build_history_summary(session)


        prompt = ChatPromptTemplate.from_template(CLASSIFICATION_PROMPT)
        chain = prompt | self._llm

        try:
            logger.info(f"[CE] topics_desc:\n{topics_desc}")
            response = chain.invoke({
                "topics_and_tasks": topics_desc,
                "history_summary": history_summary,
                "query": query
            })
            text = response.content.strip()

            # 从LLM输出中提取 JSON（防止输出了多余的文字）
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                topic_name = result.get("topic_name", "通用咨询")
                task_name = result.get("task_name", "通用回答")
                llm_tool = result.get("tool", "get_other")

                # 关键：不用LLM给的 tool, 该有代码从配置表
                tool_name = self._resolve_tool(biz_code, task_name, llm_tool)
                return (
                    result.get("topic_name", "通用咨询"),
                    result.get("task_name", "通用回答"),
                    result.get("tool", "get_other"),
                )

        except Exception as e:
            logger.warning(f"意图识别失败,降级到通用回答:{e}")
        return "通用咨询", "通用回答", "get_other"

    def _resolve_tool(self, biz_code: str, task_name: str, llm_tool: str) -> str:
        """
        从 task.yaml 里用 task_name 查对应的 tool

        为什么这样做：
        - LLM 判断 task_name (中文匹配中文) 比较准确
        - LLM 输出 tool 名（英文字符串）容易自由发挥
        - 改由代码从配置文件精准查找，完全绕开LLM的不稳定性
        """
        biz_config = self._tasks_config.get("biz_codes", {}).get(biz_code, {})
        for topic in biz_config.get("topic", []):
            for task in topic.get("tasks", []):
                if task["name"] == task.name:
                    logger.info(f"[CE] task 映射命中，task={task_name} -> tool={task['tool']}")
                    return task['tool']

        # task_name 也对不上（LLM 连 task都编了）
        # 最后用 LLM 给的 tool名试一次，找不到就降级
        from agents.tool_registry import ToolRegistry
        ToolRegistry.init()
        if llm_tool in ToolRegistry._registry:
            return llm_tool

        logger.warning(f"[CE] task=[{task_name}] 未匹配任何配置，降级 get_other")
        return 'get_other'

    def _task_needs_confirm(self, biz_code: str, task_name: str) -> bool:
        """查 tasks.yaml，判断该任务是否配置了 confirm: true"""
        biz_config = self._tasks_config.get("biz_codes", {}).get(biz_code, {})
        for topic in biz_config.get("topics", []):
            for task in topic.get("tasks", []):
                if task["name"] == task_name:
                    return bool(task.get("confirm", False))
        return False

    def _is_confirmed(self, query: str) -> bool:
        """判断用户本轮输入是「确认」还是「取消」，取消词优先"""
        q = query.strip().lower()
        for w in _CANCEL_WORDS:
            if w in q:
                return False
        for w in _CONFIRM_WORDS:
            if w in q:
                return True
        return False # 都匹配不上，保守视为取消

    # 主入口
    def handle(self, query: str, context: ContextInfo):
        """
        上下文工程主处理方法
        被 Dispatcher 在工具执行之前调用
        """
        biz_code = context.request_info.biz_code()
        session = self.get_or_create_session(context=context)

        # 1. 直接路由（如请求参数已指定工具，跳过LLM识别）
        if direct_tool := context.get_param("direct_tool"):
            session.tool_name = direct_tool
            logger.info(f"直接路由：tool:{direct_tool}")
            return session

        # 2. 待确认状态处理（第 N+1 轮）
        # session.pending_confirm 是上一轮写入并缓存的，这里读取
        if session.pending_confirm:
            if self._is_confirmed(query=query):
                # 用户确认 -> 恢复工具名, 把原始 query 通过 context 传给 dispatcher
                session.tool_name = session.pending_confirm_tool
                context.add_param("confirmed_query", session.pending_confirm_query)
                context.add_param("confirmed", True)
                logger.info(f"[confirm] 用户确认，执行 tool={session.pending_confirm_tool}")
            else:
                # 用户取消 -> 只发信号,despatcher 推送取消提示
                context.add_param("confirm_aborted", True)
                logger.info(f"[confirm] 用户取消")

            # 无论确认还是取消，都清空待确认状态
            session.pending_confirm = False
            session.pending_confirm_tool = ""
            session.pending_confirm_query = ""
            self.save_session(context=context)
            return session

        # 3. LLM意图识别
        topic_name, task_name, tool_name = self._classify(query, biz_code, session=session)
        session.set_topic_and_task(topic_name, task_name, tool_name)
        logger.info(f"意图识别:topic={topic_name}, task={task_name}, tool={tool_name}")

        # 4. confirm 检查(第 N 轮)
        if self._task_needs_confirm(biz_code=biz_code, task_name=task_name):
            session.pending_confirm = True
            session.pending_confirm_tool = tool_name
            session.pending_confirm_query = query
            context.add_param("need_confirm", True)
            context.add_param(
                "need_confirm_msg",
                f"⚠️ 您确定要执行【{task_name}】操作码？\n"
                f"原始请求:「{query}」\n\n"
                f"请回复「确认」继续，回复「取消」放弃。"
            )
            self.save_session(context=context) # 必须保存，否则第N+1轮读不到pending_confirm
            logger.info(f"[confirm] 任务「{task_name}」等待用户确认")
            return session

        # 5. 普通任务直接执行，保存session
        self.save_session(context=context)
        return session


# 全局单例
context_manager = ContextManager()




