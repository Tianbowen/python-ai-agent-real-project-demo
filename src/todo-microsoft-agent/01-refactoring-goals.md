# 重构目标

## todo-agent原项目主要链路

```txt
FastAPI
    -> Dispatcher
    -> ContextManager 意图分类
    -> ToolRegistry
    -> LangChain/LangGraph 工具
    -> TodoDB
    -> SSE
```

## 新项目链路

```txt
FastAPI
    -> Microsoft Agent Framework
    -> Typed Function Tools
    -> TodoService
    -> TodoRepository
    -> SSE
```

## 主要替换

- **LangChain ChatOpenAI**  -> **OpenAIChatCompletionClient**
- 自定义**ToolRegistry** -> MAF **tools**
- 自定义会话历史 -> **AgentSession**
- LangGraph -> MAF Wrokflow
- 删除确认逻辑 -> Tool Approval(工具批准)
- 原有 FastAPI、SSE、Web UI思路继续保留

核心设计原则：LLM只负责理解语言和选择工具，TODO的增删改查必须由业务代码确定性执行。
