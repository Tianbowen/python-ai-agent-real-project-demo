# 实现SSE的效果
"""
    需要安装
    fastapi web框架
    sse-starlette 用于实现Server-Sent Events(SSE) 功能
    uvicorn 用于运行 FastAPI应用的 ASGI服务器

    访问：localhost:5000/stream
"""

import asyncio
from fastapi import FastAPI
from sse_starlette import EventSourceResponse
import uvicorn

app = FastAPI()

@app.get("/stream")
async def stream():
    async def generator():
            words =  ["你", "好", "，", "我", "是", "A", "I", "助", "手"]
            for word in words:
                  await asyncio.sleep(0.2)
                  yield word # SSEResponse 会自动加 "data:" 前缀
            yield "[DONE]"

    return EventSourceResponse(generator())

if __name__ == "__main__":
      uvicorn.run(app, host="0.0.0.0", port=5000)