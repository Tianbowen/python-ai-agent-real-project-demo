# 目录结构

```txt

todo-microsoft-agent/
├── app/
│   ├── __init__.py
│   ├── domain/
│   ├── repositories/
│   ├── services/
│   ├── agent/
│   ├── workflows/
│   ├── api/
│   └── static/
├── tests/
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
└── main.py

```

各目录职责：
- domain：todo 数据模型和业务枚举
- repositories：数据保存与查询
- services：确定性业务规则
- agent：MAF 客户端，工具和Agent
- workflows：批量、并行、条件流程
- api：FastAPI 与 SSE
- static：聊天页面
- tests：不依赖真实模型的测试

## 创建环境并运行

```txt
cd ".....\src"

# 1. 创建虚拟环境(默认 .venv)
uv venv --python 3.11 # 如果默认用最新版本python：uv venv

# 2. 激活 (可选； 也可不加激活，直接用 uv run)
.\.venv\Script\Activate.ps1

# 3. 按 pyproject.toml 安装目录 + 开发依赖
uv sync --extra dev

# 4. 准备环境变量
Copy-Item .env.example .env
# 编辑 .env, 填写真实API Key

# 5. 运行方式任选其一：

# 方式A：已激活 .venv
python main.py

# 方式B：不激活，推荐日常使用
uv run python main.py
```

## Agent vs Workflow

|  | Agent | Workflow |
| -- | -- | -- |
| 决策方式 | 模型动态选工具 | 你写死的执行顺序 |
| 适合 | 开放式对话 | 固定业务步骤 |
| 示例 | "帮我整理下待办" | 查今日待办 -> 并行统计 -> 汇总 |

**Todo项目中两者并存： 日常对话用Agent；**

![alt text](../images/devui-chat-screenshot.png)
![alt text](../images/devui-chat-screenshot-1.png)
![alt text](../images/devui-chat-screenshot-2.png)

## Functional Workflow(函数式工作流)

**知识点：**

- @workflow: 把普通async 函数变成可 .run()的 Workflow
- 输入的第一个参数；返回值自动作为output
- asyncio.gather：官方推荐的并行写法(Functional API)

## Functional Workflow vs Graph WorkflowBuilder

| Functional @workflow | Graph WorkflowBuilder |
| -- | -- |
| 一个 async 函数里写 if | 多个 exector + add_edge |
| 适合快速原型 | 适合固定拓扑、DevUI原生发现 |

**关键API：**
- @executor: 图上的处理节点
- ctx.send_message(...)：发给下游节点
- ctx.yield_output(...)：工作流最终输出
- WorkflowBuilder(...).add_edge(...).build()：组装图
- 
![alt text](../images/devui-workflow-graph-screenshot.png)
![alt text](../images/devui-workflow-graph-screenshot-2.png)

## 已学知识点回顾
| 概念 | 关键 API|
| -- | -- |
| 挂起工作流 | await ctx.request_info(data, type, request_id=...) |
| 读取挂起状态 | result.get_final_state() == WorkflowRunState.IDLE_WITH_PENDING_REQUESTS |
| 读取挂起的请求 | result.get_request_info_events() |
| 拒绝/同意恢复 | workflow.run(responses={"request_id": True/False}) |

## Context Provider - 上下文提供程序

### 核心作用：解决"记忆"与"知识"问题

- 长期/外部记忆：让智能体"记住"用户偏好或从外部知识库(如数据库，搜索引擎)检索信息。
- 动态上下文注入：在每次对话前，动态添加指令、工具或数据，以影响智能体的行为。

问题场景：TodoAgent 的 instructions 是硬编码字符串，Agent 不知道今天是几号。用户说"明天到期"，靠的是 TodoService.parse_due_date() 在工具层解析——但如果用户问"今天有什么待办"，模型就不知道"今天"是哪一天。

解决方案：ContextProvider.before_run() 在每次模型调用前注入动态上下文，不污染静态instructions(指智能体初始化时硬编码写死的，在运行过程中不会动态改变的系统提示词)

```txt

每次 AgentSession.send_message()
        │
        ▼
ContextProvider.before_run() <- 注入今日日期、用户名等
        │
        ▼
    模型推理
        │
        ▼
ContextProvider.after_run() <- 可选：处理响应、存数据
```
**本节完整知识点 执行时序**

```txt

agent.run(msg, session=session)
        │
        ├─ TodayDateProvider.before_run()  → extend_instructions("今天是 2026-07-22")
        ├─ UserNameProvider.before_run()   → extend_instructions("用户是小明")
        │
        ▼
   模型推理（拿到拼装后的 instructions）
        │
        ▼
   ContextProvider.after_run()   ← 本节未用，下节讲

```

**三个核心方法**
| 方法 | 用途 |
| context.extend_instructions(source_id, text) | 追加系统级提示词 |
| context.extend_messages(source_id, messages) | 注入历史消息（如摘要、示例）|
| context.extend_tools(source_id, tools) | 动态注入工具（按会话权限控制）|

**state 字典（跨轮次）**
before_run / after_run 都收到 state: dict，这个字典在同一个 Provider 实例的生命周期内跨轮次保留，可以用来做计数、缓存等：

```python

async def before_run(self, *, agent, session, context, state):
    state["call_count"] = state.get("call_count", 0) + 1
    context.extend_instructions(self.source_id, f"这是第 {state['call_count']} 次对话。")

```
