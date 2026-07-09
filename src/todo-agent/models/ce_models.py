# models/ce_models.py
# 上下文工程状态机

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

@dataclass
class Slot:
    """
    槽位：从对话中提取出的关键参数

    比如用户说"明天下午3点开会"， 提取出：
    - code= "title", value="开会"
    - code= "due_date", value="明天下午3点"
    """

    code: str # 参数编码(程序使用)
    name: str # 参数名称(人类可读)
    value: Any = None # 当前提取到的值(None= 未提取到)
    required: bool = False

@dataclass
class Task:
    """
    任务：用户当前正在执行的具体操作
    一个主题下可以有多个任务，但同一时刻只有一个是活跃的
    """

    code: str
    name: str
    tool: str = "get_other"
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    slots: Dict[str, Slot] = field(default_factory=dict)

    def slot_value(self, code: str, default: Any = None) -> Any:
        """获取某个槽位的值，未提取到则返回默认值"""
        slot = self.slots.get(code)
        return slot.value if (slot and slot.value is not None) else default
    
    def missing_required_slots(self) -> List[str]:
        """返回还未填充的必填槽位名称列表（用于追问用户）"""
        return [
            s.name for s in self.slots.values()
            if s.required and s.value is None
        ]
    
@dataclass
class Topic:
    """
    主题：用户当前聊的大方向
    比如"我想管理任务"就是一个主题，主题发生变化时会重置任务状态
    """

    name: str
    topic_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    current_task: Optional[Task] = None

@dataclass
class ConversationSession:
    """
    对话会话：一次完整对话的全部状态

    该对象会被序列化存入缓存(TTLCache)
    下一轮请求来时从缓存恢复，实现多轮记忆

    核心字段:
    - chat_hsitory: LangChain 格式的历史消息(供 LLM 看)
    - current_topic: 当前主题 (供上下文工程用)
    - tool_name: 最终路由到的工具名(给工具注册中心用)
    """

    user_id: str
    session_id: str

    current_topic: Optional[Topic] = None
    tool_name: str = "get_other" # 默认路由到通用问答

    # 待确认状态 -- 用于 confirm: true 的两轮交互
    # 第N轮写入，第N+1轮读取后清空

    pending_confirm: bool = False # 是否正在等待用户确认
    pending_confirm_tool: str = "" # 待执行的工具名(确认后路由到它)
    pending_confirm_query: str = "" # 用户原始输入(确认后原样传给工具)

    # LangChain 官方的内存历史对象, 直接塞进 Prompt 的 MessagesPlaceholder


    chat_history: InMemoryChatMessageHistory = field(
        default_factory= InMemoryChatMessageHistory
    )

    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # 快捷访问

    def topic_name(self) -> Optional[str]:
        return self.current_topic.name if self.current_topic else None
    
    def current_task(self) -> Optional[Task]:
        if self.current_topic:
            return self.current_topic.current_task
        return None
    
    def task_name(self) -> Optional[str]:
        task = self.current_task()
        return task.name if task else None
    
    def slot_value(self, code: str, default: Any = None) -> Any:
        task = self.current_task()
        return task.slot_value(code, default) if task else default
    
    # 状态更新

    def set_topic_and_task(self, topic_name: str, task_name: str, tool: str):
        """
        更新当前主题和任务
        如果主题变了，丢弃旧的task(重置槽位)，开始新任务
        """        
        # 主题变化 -> 新建主题
        if not self.current_topic or self.current_topic.name != topic_name:
            self.current_topic = Topic(name=topic_name)
        task = Task(code=task_name, name=task_name, tool=tool)
        self.current_topic.current_task = task
        self.tool_name = tool
        self.updated_at = time.time()

    def add_history(self, query: str, answer: str):
        """追加一轮对话到历史"""
        self.chat_history.add_user_message(query)
        self.chat_history.add_ai_message(answer)

    def get_recent_history(self, max_turns: int = 5) -> List:
        """取最近N轮对话"""
        messages = self.chat_history.messages
        return messages[-(max_turns * 2):]
