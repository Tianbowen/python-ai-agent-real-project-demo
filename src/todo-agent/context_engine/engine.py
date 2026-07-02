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
                return (
                    result.get("topic_name", "通用咨询"),
                    result.get("task_name", "通用回答"),
                    result.get("tool", "get_other"),
                )

        except Exception as e:
            logger.warning(f"意图识别失败,降级到通用回答:{e}")
        return "通用咨询", "通用回答", "get_other"
    
    # 主入口
    def handle(self, query: str, context: ContextInfo):
        """
        上下文工程主处理方法
        被 Dispatcher 在工具执行之前调用
        """
        biz_code = context.request_info.biz_code()
        session = self.get_or_create_session(context=context)

        # 直接路由（如请求参数已指定工具，跳过LLM识别）
        if direct_tool := context.get_param("direct_tool"):
            session.tool_name = direct_tool
            logger.info(f"直接路由：tool:{direct_tool}")
            return session
        
        # LLM意图识别
        topic_name, task_name, tool_name = self._classify(query, biz_code, session=session)
        session.set_topic_and_task(topic_name, task_name, tool_name)

        logger.info(f"意图识别:topic={topic_name}, task={task_name}, tool={tool_name}")
        return session
    

# 全局单例
context_manager = ContextManager()



    
        