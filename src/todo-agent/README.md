# 总结

## 整体架构

```txt
HTTP请求
    │
    ▼
Dispatcher <- 限流 + 解析参数 + 校验
    │
    ▼
ContextManager <- 恢复会话 + LLM 意图识别 + tool_name
    │
    ▼
ToolRegistry <- tool_name -> 工具类实例
    │
    ▼
AbstractTool.arun() <- 查DB + 调LLM(流式)
    │
    ▼
StreamCallbackHandler (asyncio.Queue)
    │ aiter()
    ▼
SSE -> 浏览器逐字显示
    │
    ▼
post_process() <- 保存对话历史 -> TTLCache
```

## 核心设计模式

### 生产者-消费者（流式输出的本质）

```python
# 生产者：工具里每生成一个token就放入队列
await self.handler.put_token(token) # -> asyncio.Queue

# 消费者：SSE 响应从队列取出推给浏览器
async for chunk in handler.aiter():
    yield chunk
```

**关键：两者解耦，生产速度和消费速度互不影响。**

### ContextVar 请求隔离

```python
# 每个请求有自己独立的数据，并发时互不污染
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# 请求进来时设置
token = request_id_ctx.set(trace_id)
# 请求结束时还原
request_id_ctx.reset(token)
```

**对比全局变量：20个并发请求，全局变量会相互覆盖，ContextVar每个协程独立一份**

### Semaphore 并发控制

```python
_SEMAPHORE = asyncio.Semaphore(20) # 最多同时处理20个请求

async def _acquire(self) -> bool:
    try:
        await asyncio.wait_for(_SEMAPHORE.acquire(), timeout=1.0)
    except asyncio.TimeoutError:
        return False # 超时 -> 拒绝请求, 告知稍后重试
```

### TTLCache 多轮记忆

```python
# 每轮对话结束后保存
set_session(f"{biz_code}:{session_id}", session)

# 下一轮请求恢复
session = get_session(cache_key)
if session is None:
    session = ConversationSession(...) # 新建
```

**会话过期时间 SESSION_TTL_S=1800 (30分钟), 超时自动清除，实现"遗忘"**

### asyncio.to_thread 避免阻塞

```python
# Langchain 的 invoke() 是同步阻塞的
# 直接在异步函数里调用会卡住整个事件循环

# 正确做法：丢到线程池执行
await asyncio.to_thread(context_manager.handle, context)
```

**规则：IO操作用await, CPU/同步阻塞操作用asyncio.to_thread**

## 上下文工程三层模型

```txt
ConversationSession(会话) -> 整个对话，存TTLCache
    Topic(主题) -> 当前聊什么方向
        Task(任务) -> 具体做什么操作
            Slot(槽位) -> 操作需要的参数
```

**关键方法**

```python
# 更新状态(主题变了会重置Task)
session.set_topic_and_task("待办查询", "查询所有待办", "get_todos")
# 取槽位值
title = session.slot_value("title") # 没有时返回None
```

## LangChain用法知识点

### LCEL管道（项目最高频用法）

```python
chain = prompt | llm # 构建链
chain.invoke({...})  # 同步调用
await chain.ainvoke({}) # 异步调用
await chain.astream({}) # 异步流式
```

### ChatPromptTemplate 三种角色

```python
ChatPromptTemplate.from_messages([
    ("system", "你是日程助手"), # 系统角色，设定 LLM 行为
    MessagesPlaceholder("history"), # 历史对话（多轮记忆）
    ("human", "{query}") # 用户当前输入
])
```

### 两种LLM实例的用途

```python
# 流式：用于生成给用户看的回答（逐字显示）
llm_stream = ChatOpenAI(streaming=True, temperature=0.7)

# 同步：用于提取信息（只需要短结果，不需要显示）
llm_sync = ChatOpenAI(streaming=False, temperature=0)
resp = await (prompt | llm_sync).ainvoke({})
```

## 路由链路（最容易出问题的地方）

```txt
tasks.yaml 的 tool 字段
     ↓ 必须完全一致
LLM Prompt 里展示的工具名
     ↓ LLM原样输出
_resolve_tool() 从task_name做二次映射（安全网）
     ↓ 必须完全一致
ToolRegistry._registry 的 key
     ↓ 必须完全一致
XxxTool.name 属性
```

**biz_code的作用：决定读tasks.yaml里的哪个产品配置**

```python
biz_config = task_yaml["biz_code"]["agents"] # bizCode = "agents"
```

前端bizCode必须与yaml key一致，否则LLM拿到空选项会乱编tool_name

## 工具类模板(每个工具的固定结构)

```python
class XxxTool(AbstractTool):
    name = "xxx" # 必须与 tasks.yaml tool 字段一致

    def __init__(self, handler=None):
        super().__init__(handler)
        self._llm = ChatOpenAI(streaming=True, ...)

    async def arun(self, query: str, **kwargs) -> None:
        # 1. 查数据
        data = db.query()

        # 2. 处理空数据 (写死回复，节省token)
        if not data:
            await self.handler.put_token("暂无数据")
            ...
            return

        # 3. 流式调用LLM
        full_text = ""
        try:
            async for chunk in chain.astream({...})
                token = chunk.content
                if token:
                    full_text += token
                    await self.handler.put_token(token)

        except Exception as e:
            error_msg = "服务暂时出现问题，请稍后再试"
            await self.handler.put_token(error_msg)
            full_text = error_msg

        # 4. 保存 + 推送结构化数据
        self.context.set_result_llm(full_text)
        await self.handler.put_data(
            biz_code=self.context.request_info.biz_code(),
            answer=full_text,
            data= [...]
        )
```

## 各文件指责

| 文件 | 指责 |
| -- | -- |
| config.py | 所有配置的唯一出口，读.env文件 |
| tasks.yaml | 业务地图，改业务只改这里 |
| models/context_info.py | 请求全局工作台，各层共享数据 |
| models/ce_models.py | 对话状态机（会话/主题/任务/槽位） |
| cache/cache.py | TTL内存缓存，实现多轮记忆 |
| callback/stream_handler.py | Queue生产消费，连接LLM和SSE |
| context_engine/engine.py | LLM意图识别 + 会话恢复 |
| agents/abstract_tool.py | 工具接口规范，子类必须实现arun() |
| agents/tool_registry.py | tool_name -> 工具类的注册表 |
| dispatch/dispatcher.py | 请求入口，串联所有环节 |
| main.py | FastAPI路由 + 生命周期管理 |