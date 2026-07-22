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