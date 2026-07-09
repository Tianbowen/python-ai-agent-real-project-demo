# 变更日志

## [2026-07-09]

### 未用，值得使用的

#### Structured Output 替换掉 re.search + json.loads

update_todo / query_todos 中提取参数的方式很脆弱，LangChain有更可靠的方法：

```python
from pydantic import BaseModel
from typing import Optional

class QueryParams(BaseModel):
    date: Optional[str] = None
    priority: Optional[str] = None
    label: Optional[str] = None

# 直接让LLM输出结构化对象，不用正则提取 regex

structured_llm = llm.with_structured_output(QueryParams)
params = await structured_llm.ainvoke(prompt)

# params.date / params.priority 直接用 不会解析失败
```

##### 知识点

llm.with_structured_output(PydanticModel) 让 LLM 直接输出符合 Pydantic 模型定义的结构化对象，彻底替代 re.search + json.loads。

```txt
旧方式：Prompt 要求输出 JSON → LLM 输出字符串 → regex 提取 → json.loads → 可能失败
新方式：LLM 内部使用 function calling 填充字段 → 直接返回 Python 对象 → 永远不会解析失败
```

#### Memory 真正接入 Prompt -- 历史对话没有喂给工具LLM

保存了历史，但工具执行时没有用到它，每次都是无记忆的单论对话。

```python
from langchain_core.prompts import MessagePlaceholder

# 原来（无记忆，每次都是全新对话）
prompt = ChatPromptTemplate.from_messages([
    ("system", "..."),
    ("human", "{query}"),
])

# 改后（多轮记忆）
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是日程助手"),
    MessagePlaceholder("chat_history"), # <- 注入历史  展开历史消息列表
    ("human", "{query}"),
])

chain = prompt | llm
chain.invoke({
    "chat_history": context.chat_history.messages,  # 传入 LangChain message 列表
    "query": query
})

```

##### 知识点

**MessagePlaceholder** 是 LangChain的占位符，会在运行时把历史消息列表展开插入Prompt, 让LLM看到上下文。



#### @tool 装饰器 + 原生 Function Calling

当前所有工具是手写Prompt 让LLM提取参数。LangChain 支持让 LLM 原生调用工具(OpenAI function calling)

```python
from langchain_core.tools import tool

@tool
def delete_todo(title_keyword: str) -> str:
    """删除标题包含关键词的待办事项"""
    item = todo_db.delete(title_keyword)
    return f"已删除: {item.title}" if item else "未找到"
```

##### 知识点

@tool 把普通Python函数声明成 LangChain工具，llm.bind_tools() 让LLM自己决定调用哪个工具，传什么参数，不再需要手写Prompt提取参数

```txt
旧方式：Prompt "帮我提取关键词" -> LLM 输出文字 -> 我们调用DB
新方式：LLM 看到工具定义 -> 直接输出 tool_call {name: "delete", args: {keyword: "买菜"}} -> 框架自动执行
```

##### 执行循环（ReAct模式）

```txt
用户输入 -> LLM思考 -> 输出 tool_call -> 执行工具 -> 把结果喂回 LLM -> LLM 生成最终回复 
```

#### 原文

```txt
未用、值得通过 Todo 项目练习的知识点
按学习优先级排列：

🔴 高优先级（核心短板）
1. Structured Output — 替换掉 re.search + json.loads

现在 update_todo / query_todos 里提取参数的方式很脆弱，LangChain 有更可靠的方法：

from pydantic import BaseModel
from typing import Optional
class QueryParams(BaseModel):
    date: Optional[str] = None
    priority: Optional[str] = None
    label: Optional[str] = None
# 直接让 LLM 输出结构化对象，不用 regex
structured_llm = llm.with_structured_output(QueryParams)
params = await structured_llm.ainvoke(prompt)
# params.date / params.priority 直接用，不会解析失败
适合改造：update_todo._extract_params()、query_todos._extract_params()

2. Memory 真正接入 Prompt — 历史对话没有喂给工具 LLM

当前 ConversationSession.chat_history 存了历史，但工具执行时的 Prompt 根本没用到它，每次都是无记忆的单轮对话。改造方式：

from langchain_core.prompts import MessagesPlaceholder
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是日程助手"),
    MessagesPlaceholder("chat_history"),   # ← 注入历史
    ("human", "{query}"),
])
chain = prompt | llm
chain.invoke({
    "chat_history": context.chat_history.messages,
    "query": query
})
适合改造：get_other（通用问答）最需要多轮记忆

3. @tool 装饰器 + 原生 Function Calling

当前所有工具是手写 Prompt 让 LLM 提取参数。LangChain 支持让 LLM 原生调用工具（OpenAI function calling）：

from langchain_core.tools import tool
@tool
def delete_todo(title_keyword: str) -> str:
    """删除标题包含关键词的待办事项"""
    item = todo_db.delete(title_keyword)
    return f"已删除：{item.title}" if item else "未找到"
llm_with_tools = llm.bind_tools([delete_todo])
这样参数提取由模型内部完成，比手写 Prompt + regex 更准确稳定

🟡 中优先级（进阶能力）
4. LangGraph — 真正的多步骤 Agent

当前项目本质是「意图识别 → 单工具执行」，LangGraph 可以实现真正的推理循环：

用户: "帮我整理一下今天的任务，优先级低的推到明天"
  ↓
LangGraph Agent:
  Step1: get_today_todos()        查今日任务
  Step2: 判断哪些优先级低
  Step3: update_todo() × N        批量修改截止日期
  Step4: 汇报结果
这是目前最前沿的 Agent 架构，适合作为本项目的终极改造目标

5. OutputParser + Pydantic 数据校验

from langchain_core.output_parsers import PydanticOutputParser
parser = PydanticOutputParser(pydantic_object=QueryParams)
prompt = prompt.partial(format_instructions=parser.get_format_instructions())
chain = prompt | llm | parser  # 自动解析 + 校验
6. LangSmith 链路追踪

在 .env 里加几个环境变量，就能在 LangSmith 平台看到每次 LLM 调用的完整输入输出、耗时、token 消耗，调试路由问题非常方便

🟢 低优先级（了解即可）
7. RunnableParallel — 并行调用

daily_summary.py 里用了 asyncio.gather，LangChain 原生也有：

from langchain_core.runnables import RunnableParallel
chain = RunnableParallel(
    todos=get_today_chain,
    stats=get_stats_chain,
)
8. Few-shot PromptTemplate — 用结构化方式管理示例，比直接写在字符串里更规范
```