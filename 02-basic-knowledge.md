# 所需掌握的技术知识

## Python语言底层

### 异步编程 asyncio

#### 必须掌握的概念

- async def / await 的含义 (协程 vs 线程的区别)
- asyncio.Semaphore -> 项目用它做并发限流
- asyncio.Task -> 项目用它并行跑 主题识别 + 槽位识别
- asyncio.create_task -> 项目用它派生 后台异步收尾任务
- asyncio.wait_for -> 项目用它做 LLM请求超时控制
- asyncio.to_thread -> 项目用它把 同步LLM调用 放线程池不阻塞事件循环
- asyncio.gather -> 并行等多个协程

### 并发：asyncio + ThreadPoolExecutor 混合模式

事件循环（async主线程）:
    - io 密集 （LLM HTTP 调用） -> asyncio 处理
    - CPU/同步阻塞(向量检索，分词) -> ThreadPoolExecutor

### contextvars - 协程安全的"请求上下文"

```python
context_vars: ContextVar[dict] = ContextVar("context_vars", default={})
```

项目隔离 每个请求上下文 的关键机制。

### 数据类（dataclass） 与 Pydantic

两种模型并用：
- @dataclass -> ConversationSession, Task, Topic, Slot (上下文工程的状态对象)
- pydantic.BaseModel -> API 请求/响应结构， LLM 输出解析

## Web框架 FastAPI

### FastAPI基础

### SSE (Server-Send Events) 流式推送

项目最关键的输出机制，不是WebSocket, 而是 SSE

```python
# 项目用 sse_starlette 实现
from sse_starlette import EventSourceResponse

return EventSourceResponse
```

**SSE原理：客户端建立一条长HTTP链接，服务器持续推送 data:...\n\n 格式的文本块，客户端逐块渲染。LLM流式输出的本质时SSE。

### Uvicorn + Gunicorn 部署模式

- uvicorn 开发
- gunicorn 生产

## LangChain（LLM编排层）

### LCEL(LangChain Expression Language) 链式编程

```python
# 项目的典型模式
chain = prompt | llm | output_parser
result = chain.invoke({"input": query})
# 或流式
async for chunk in chain.astream({"input": query}):
    yield chunk
```

必须掌握的组件：
- ChatPromptTemplate.from_messages() => 构建多角色 Prompt
- MessagesPlaceholder -> 插入对话历史
- ChatOpenAI / ChatGLM 等 LLM对象
- 各种 OutputParser (PydanticOutputParser, JsonOutputParser 等)
- RunnableWithMessageHistory -> 带历史记录的链

### BaseTool（智能体工具接口）

```python
from langchain_core.tools import BaseTool

class GetOtherTool(BaseTool):
    name: 'get_other',
    description = '通用问答工具'，

    async def _arun(self, *args, **kwargs):
        # 具体业务

```
每新增一个业务能力 = 新写一个 AbstractTool 子类

### InMemoryChatMessagehistory （对话历史管理）

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
# 项目用它存储每个会话的对话轮次
```

### Callbacks (回调机制)

项目的流式输出依赖 LangChain 的Callback机制：

```python
LLM 生成 token -> on_llm_new_token() 回调
                -> 放入 asyncio.Queue
                  -> SSEtreamer 从 Queue 取 -> 推送给客户端
```

## 存储与缓存

### SQLAlchemy ORM (关系型数据库)

最小集需要理解：
- declarative_base() -> 定义 ORM Model
- SessionLocal -> 获取 DB Session
- CRUD操作
- 连接池配置(pool_size / pool_recycle / pool_pre_ping)

项目用到表： message(对话记录) knowledge_base(知识库)

### Redis (分布式缓存)

项目用途：
- 存储会话上下文（对话历史，槽位状态） - 跨进程共享
- 用户画像快照的L2缓存

```python
redis.set(key, value, ex=ttl) # 写入并设置过期时间
redis.get(key) # 读取
redis.delete(key) # 删除
```

### cachetools TTLCache(进程内 L1缓存)

```python
from cachettools import TTLCache
# 进程内， 毫秒级命中，项目用来缓存高频读取的会话和配置
cache = TTLCache(maxsize=9999, ttl=3600)
```

### 三级缓存架构理解

读取顺序:
L1(TTLCache, 微秒) -> L2(Redis, 毫秒) -> L3(PostgreSQL, 毫秒~百毫秒)

## 领域模型涉及(架构层)

项目最核心的自研， 不在任何开源项目里。

### 请求上下文对象 ContextInfo

一次请求的全部状态都挂在这个对象中：

ContextInfo
- request_info -> 请求入参(query, orgCode, patientId等)
- chat_history -> 本会话对话历史
- cache_data -> 从 Redis/缓存恢复的会话状态
- ctx -> 从 ConversationSession (上下文工程状态机)
- response_infos -> 待输出的响应数据
- 
理解这个类 = 理解整个请求生命周期

### 对话状态机 ConversationSession -> Topic -> Task -> Stage -> Slot

层级关系：
ConversationSession (整个会话)
    -[ Topic (主题， 如挂号)
        -[ Task (任务，如"查医生排班")
            -[ Stage （阶段, 如"已知科室，待选日期"）      
            -[ Slots (槽位变量， 如 dept_name="心内科")
序列化后存入 Redis，下次请求恢复 -> 实现多轮对话记忆

### StreamCallbackHandler 流式控制器

核心设计：
LLM生成 -> on_llm_new_token -> asyncio.Queue.put()
                                    |
                                SSEtreamer.aiter()
                                    |
                                EventSourceResponse -> 客户端
理解生产者-消费者模型，是理解整个流式输出的关键

### TaskPoolExecutor 线程池调用器

解决问题：
asyncio 事件循环不能被阻塞
    -> 同步 IO(LLM HTTP) / CPU 密集 (向量检索) 需要在线程池里跑
    -> 但线程池没有 contextvars (请求上下文会丢失)
    -> 解决方案：ctx = contextvars.copy_context(), 在线程里执行 ctx.run(fn)


## 业务配置化驱动

### YAML配置驱动的任务路由

config/tasks.yaml 是整个业务的"地图"。需要理解它的结构：

```YAML
biz_codes:
  - agents:
      topics:
        - name: 挂号查询
          task:
            - name: 查询医生
              tool: get_doctor
              slots:
                - code: dept_name
                  name: 科室名称
```

需要能读懂这个YAML，理解它如何被 TaskConfigLoader 解析成 Python 对象

### Pydantic 结构化输出 Parser

```python
# 项目用 LLM 做分类，但要求输出结构化 JSON
class TopicClassificationResult(BaseModel):
    topic_name: str

parser = PydanticOutputParser(TopicClassificationResult)
chain = prompt | llm | parser
result = TopicClassificationResult = chain.invoke(...)
```

LLM的输出需要被强制解析成结构体，失败要处理 -> 是 LLM Agent 可靠性的关键手段