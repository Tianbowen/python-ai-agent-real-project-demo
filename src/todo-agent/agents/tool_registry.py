# agents/tool_registry.py
# 工具注册中心

from typing import Dict, Type, Optional

from agents.abstract_tool import AbstractTool
from callback.stream_handler import StreamCallbackHandler
from config import logger

class ToolRegistry:
    """
    工具注册中心：管理工具名称到工具类的映射

    对应原项目的 AgentServiceFactory 简化了授权校验逻辑
    """

    _registry: Dict[str, Type[AbstractTool]] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, tool_cls: Type[AbstractTool]):
        """注册一个工具类（装饰器方式或手动调用）"""
        cls._registry[tool_cls.name] = tool_cls
        logger.info(f"注册工具: {tool_cls.name}")

    @classmethod
    def init(cls):
        """初始化：扫描并注册所有工具"""
        if cls._initialized:
            return
        # 手动注册 (生产环境可改为自动扫描子类)
        from agents.get_other import GetOtherTool
        cls.register(GetOtherTool)
        # 在这里注册更多工具
        # from agents.get_todo_list import GetTodoList
        # cls.register(GetTodoList)

        from agents.get_todos import GetTodosTool
        cls.register(GetTodosTool)
        from agents.create_todo import CreateTodoTool
        cls.register(CreateTodoTool)
        from agents.get_today_todos import GetTodayTodosTool
        cls.register(GetTodayTodosTool)
        from agents.complete_todo import CompleteTodoTool
        cls.register(CompleteTodoTool)

        from agents.batch_complete_todo import BatchCompleteTodoTool
        cls.register(BatchCompleteTodoTool)
        from agents.daily_summary import DailySummaryTool
        cls.register(DailySummaryTool)
        from agents.smart_todo import SmartTodoTool
        cls.register(SmartTodoTool)

        from agents.update_todo import UpdateTodoTool
        cls.register(UpdateTodoTool)
        from agents.delete_todo import DeleteTodoTool
        cls.register(DeleteTodoTool)

        from agents.query_todos import QueryTodosTool
        cls.register(QueryTodosTool)

        from agents.tool_agent import ToolAgentTool
        cls.register(ToolAgentTool)

        from agents.lang_graph_agent import LangGraphAgentTool
        cls.register(LangGraphAgentTool)
        
        cls._initialized = True
        logger.info(f"工具注册完成，共{len(cls._registry)} 个工具: {list(cls._registry.keys())}")

    @classmethod
    def get(cls, tool_name: str, handler: StreamCallbackHandler) -> AbstractTool:
        """根据工具名获取工具实例，找不到降级到 get_other"""
        cls.init()
        tool_cls = cls._registry.get(tool_name)
        if tool_cls is None:
            logger.warning(f"工具{tool_name} 未注册，降级使用 get_other")
            tool_cls = cls._registry.get("get_other")
        if tool_cls is None:
            # raise 主动触发异常关键字
            # RuntimeError 内置的异常类型 系统级别的错误
            raise RuntimeError("get_other 工具未注册，系统配置错误")
        return tool_cls(handler=handler)