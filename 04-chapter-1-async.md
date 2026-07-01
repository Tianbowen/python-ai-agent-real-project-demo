# 异步，SSE, 上下文工程

## 异步

### 普通def,而用 async def

LLM调用就是"厨房"，等待响应需要3秒以上，如果用同步，20个用户同时请求时就需要20个线程，等于前19个用户干等，**资源浪费巨大**，用asyncio, 同一个线程可以交替处理所有请求，在LLM思考期间去处理别的事情。

```python
# 同步 第一个用户在等待时，第二个用户被阻塞
def handle(query):
    result = call_llm(query)
    return result

# 异步 第一个用户在等待时，CPU 去做别的事
async def handle(query):
    result = await call_llm(query)
    return result
```

关键区分:
- await = "我要等一个网络/IO操作，这期间把CPU让出去"
- asyncio.to_thread() = "这是CPU密集型任务，丢到线程池，避免阻塞事件循环"

### 用SSE，而不是普通HTTP

- 普通响应：你点了外卖，等30分钟，外卖员一次性全部送来
- SSE (Server-Sent Events): 外卖员每做好一道菜就立刻送来，不用等全部做完。

LLM是按 token (约1-2个字) 逐步生成的，如果等全部生成再返回：
- 用户要等待10-20秒看到空白屏幕
- 用户体验极差

SSE让每生成一个token就立刻推给客户端：用户看到"打字机"效果，感觉非常流畅。
SSE的数据格式(HTTP的长连接，每行以data:开头)
```python
data: {"token": "今"}
data: {"token": "天"}
data: {"token": "你"}
data: {"token": "有"}
data: [DONE]
```
### 什么是上下文工程，为什么不是普通Prompt?

普通Prompt：你每次都要告诉LLM完整的指令，LLM对每次对话是无状态的
上下文工程解决的问题：多轮对话中，用户说的往往是不完整的
```txt
第1轮：用户："帮我添加一个任务" -> LLM不知道添加什么
第2轮：用户："明天下午3点开会" -> LLM不知道这和第1轮有关
第3轮：用户："高优先级的" -> 这个 "高优先级"指的是哪个任务？
```

上下文工程要做的事：
1. 识别主题(Topic)：用户在讨论什么大方向？ "日程管理"
2. 识别任务(Task)：具体要做什么操作？ -> "创建任务"
3. 提取槽位(Slot)：操作需要哪些参数？ -> {time: "明天下午3点", priority: "高"}
4. 路由工具(Tool)：调用哪个能力？-> create_todo

```txt
用户输入
    ↓
[意图识别 LLM] -> Topic: 任务管理 -> Task: 创建任务 -> Tool: create_todo
    ↓
[槽位提取] -> {title: "开会"， time: "明天15:00", priority: "高"}
    ↓
[工具执行] -> 调用 create_todo(title, time, priority)
    ↓
[流式响应] -> "好的，我已为您创建..."
```

### 什么是ContextInfo? 为什么要用它？

问题：1个http请求要经过10几个函数/类，你怎么传递请求相关的数据？
- 方案A: 每个函数都增加参数 -> 参数爆炸，改一处改处处
- 方案B: 全局变量 -> 并发时数据相互污染(用户A看到用户B的数据)
- 方案C(正确)：ContextInfo + contextvars -> 每个协程有自己的隔离副本

```python
# contextvars 工作原理

from contextvars import ContextVar

_ctx: ContextVar = ContextVar("ctx")

# 请求1 和 请求2 同时运行，互不打扰
async def request_1():
    _ctx.set({"user": "张三"})
    await some_long_operation() # 此时请求2在执行
    print(_ctx.get()) # 仍然时 user: 张三,不会变成李四的数据

async def request_2():
    _ctx.set({"user": "李四"})
    # ...
```

## 整体数据流

```txt
HttP Post /chat
    ↓
    Dispatcher 1. 限流(Semaphore) 2. 解析参数 -> ContextInfo
    ↓
    ContextManager 3. LLM意图识别 -> 写入 ctx.tool_name    
    ↓
    ToolRegistry 4. 根据 tool_name 找到工具类
    ↓
    AbstractTool.arun() 5. 执行业务逻辑 (查DB/调API/调LLM)    
    ↓
    StreamCallbackHandler.put_token() 6. 生产者： 放入 asyncio.Queue    
    ↓
    SSE Response aiter() 7. 消费者：从Queue取出推出客户端
    ↓
    ProcessProxy.post_process() 8. 保存会话历史到缓存(下轮对话用)
```

