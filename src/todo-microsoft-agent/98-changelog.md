[2026-07-15]
先纠正 UI 方案
CopilotKit 不是 Microsoft Agent Framework 自带 UI，而是其官方推荐的 AG-UI 生态集成。

建议分两阶段学习：

开发与调试阶段：使用官方 DevUI

不写 FastAPI
不写 SSE
不写前端
直接调试 Agent、工具和 Workflow
完整应用阶段：AG-UI + CopilotKit

CopilotKit 提供 React UI
Next.js 提供 Copilot Runtime
Python 端使用官方 agent-framework-ag-ui
Python 官方 AG-UI 适配器内部仍依赖 FastAPI，但我们不自己设计 API 或 SSE
因此，现在删除原计划中的自建 FastAPI、静态 HTML 和 SSE 实现。

重新规划后的学习路线
阶段一：基础 Agent，已完成
你已经学会：

OpenAIChatCompletionClient
DeepSeek/OpenAI 兼容端点
Agent
instructions
agent.run()
@tool
Annotated + Field
AgentSession
多轮工具调用
对应官方示例：

01_hello_agent.py
02_add_tools.py
03_multi_turn.py
阶段二：确定性业务内核，已完成
当前已经完成：

Todo 领域模型
Priority 和 TodoStatus
TodoRepository
MemoryTodoRepository
TodoService
相对日期确定性解析
领域异常
pytest 单元测试
这些不是 MAF 特有技术，但必须保留，因为 Agent 不应该直接承担业务规则。

阶段三：官方 Agent Tools，当前阶段
下一步完成：

修复当前 tools.py
目前仍直接调用旧仓库 API
必须改为调用 TodoService
实现官方 Typed Function Tools：
create_todo
list_todos
complete_todo
update_todo
delete_todo
batch_complete_todos
today_summary
学习：
Tool schema
工具异常
结构化返回
工具调用事件
动态工具暴露
为删除工具增加官方审批：
@tool(approval_mode="always_require")
def delete_todo(...):
    ...
这里不再自己写“是否确认”的对话状态机。

阶段四：官方 DevUI
完成工具后立即接入 DevUI。

新增依赖：

uv add --prerelease=allow agent-framework-devui
项目组织为官方目录发现结构：

entities/
└── todo_agent/
    └── __init__.py
其中必须导出：

agent = Agent(...)
启动：

uv run devui ./entities --reload
DevUI 将负责：

Web 聊天界面
流式显示
会话测试
工具调用展示
Agent 和 Workflow 调试
OpenAI-compatible API
这一阶段不需要 FastAPI、SSE 或前端代码。

阶段五：Session、History 和 Context Provider
继续学习官方对话上下文体系：

AgentSession
会话隔离
序列化和恢复
session state
HistoryProvider
历史消息加载与保存
ContextProvider
执行前注入用户偏好
执行后提取信息
动态添加消息、工具和 middleware
TODO 应用练习：
记住用户默认优先级
记住用户昵称
自动注入当前日期
每个会话隔离待办数据
这里会取代目前依靠提示词猜测日期的方式。

阶段六：Middleware
分别学习官方三层中间件：

Agent middleware：日志、权限、耗时
Function middleware：工具参数校验、审计
Chat middleware：模型请求重试、模型调用记录
TODO 应用实践：

用户请求
→ Agent 日志中间件
→ Context Provider
→ 模型
→ Function 审计中间件
→ Todo 工具
不会为了使用技术而滥用 middleware，每层只放横切关注点。

阶段七：Workflow
按官方顺序学习两种 API。

7.1 Functional Workflow
使用：

@workflow
@step
普通 if/else
循环
asyncio.gather
实现：

今日摘要并行统计
智能创建或完成
批量完成流水线
7.2 Graph Workflow
学习：

WorkflowBuilder
Executor
Edge
条件路由
Workflow event
类型安全消息
Checkpoint
Resume
Human-in-the-loop
项目中将导出：

entities/
├── todo_agent/
│   └── __init__.py
└── todo_workflow/
    └── __init__.py
然后两者都能被 DevUI 自动发现。

阶段八：多 Agent 编排
使用 TODO 场景学习官方 orchestration：

Sequential
Concurrent
Handoff
Group Chat
Agent as Tool
不会强行把所有模式用于最终项目。每种模式先做最小实验，再判断是否适合 TODO。

最终项目可能只保留：

单 Todo Agent
一个摘要 Agent
一个显式 Workflow
阶段九：可观测性与质量
学习官方能力：

OpenTelemetry
Agent trace
模型耗时
token 使用
工具执行 span
Workflow span
敏感数据控制
Evaluation
测试分层：

TodoService 单元测试
→ Tool 契约测试
→ Agent 假模型测试
→ Workflow 测试
→ 少量真实模型验收
阶段十：官方协议与集成
分别学习：

MCP
把 TODO 能力暴露成 MCP 工具，或连接第三方 MCP Server。

A2A
学习 Agent 与远程 Agent 通信。只做独立示例，不强行用于单体 TODO。

AG-UI
理解 Agent 与 UI 之间的标准事件协议：

流式文本
工具调用
状态同步
HITL
Generative UI
阶段十一：CopilotKit 完整 UI
最后再引入：

CopilotKit React
→ Next.js Copilot Runtime
→ HttpAgent
→ MAF AG-UI Endpoint
→ TodoAgent
使用：

agent-framework-ag-ui
@copilotkit/react-core
@copilotkit/react-ui
@copilotkit/runtime
@ag-ui/client
此阶段才创建真正面向用户的 TODO 界面。

需要注意：Python 官方 AG-UI endpoint 仍通过 FastAPI 托管，但它只是官方适配器，不再由我们编写 /api/chat、SSE 协议和路由逻辑。

阶段十二：官方托管
最后了解官方生产托管：

Azure Functions
Durable Task
Foundry
A2A hosting
身份认证和会话所有权
持久化 checkpoint
这部分先学习官方最小示例，不要求 TODO 项目必须部署 Azure。

依赖调整
当前暂时移除未使用的自建 Web 依赖：

uv remove fastapi uvicorn sse-starlette httpx
加入 DevUI：

uv add --prerelease=allow agent-framework-devui
暂时保留：

agent-framework
python-dotenv
pytest
pytest-asyncio
agent-framework-ag-ui 和 CopilotKit 等到最终 UI 阶段再安装。