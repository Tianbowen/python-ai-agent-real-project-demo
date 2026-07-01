# 单独理解核心机制

## 技术基础总结

在playground文件夹下，完成四个实验，构建整个框架的全部底层积木：

| 积木 | 用途 | 关键API |
| -- | -- | -- |
| asyncio.Queue | LLM token -> SSE的传输通道 | put() / get() |
| contextvars.ContextVar | 请求隔离，替代全局变量 | .set() / .get() |
| EventSourceResponse | HTTP长连接，推送 token | yield |
| chain.astream() | LangChain流式LLM调用 | async for chunk |

