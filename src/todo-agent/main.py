# main.py
# FastAPI 入口 + 启动

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Dict

import uvicorn
from fastapi import FastAPI, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agents.tool_registry import ToolRegistry
from config import API_HOST, API_PORT, logger, request_id_ctx
from dispatch.dispatcher import dispatcher

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 应用声明周期

@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化，关闭时清理"""
    logger.info("=== mini-todo-agent 启动中 ===")
    ToolRegistry.init() # 注册所有工具
    logger.info("=== mini-todo-agent 启动完成 ===")
    yield
    logger.info("=== mini-todo-agent 关闭 ===")

# FastApi 应用

app = FastAPI(
    title="mini-todo-agent",
    version="0.1.0",
    lifespan=lifespan
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 允许跨域（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 中间件：每个请求注入 trace_id

@app.middleware("http")
async def inject_trace_id(request: Request, call_next):
    trace_id = request.headers.get("X-Request-Id", uuid.uuid4().hex)
    token = request_id_ctx.set(trace_id)

    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = trace_id
        return response
    finally:
        request_id_ctx.reset(token)

# 路由

@app.get("/", response_class=FileResponse)
async def index():
    """打开浏览器访问 http://localhost:5000 直接进入聊天界面"""
    return "static/index.html"

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mini-todo-agent"}


@app.post("/api/chat")
async def chat_stream(request: Request, data: Dict = Body(...)):
    """
    主对话接口（SSE 流式响应）
    
    请求示例：
    {
        "query": "心内科怎么挂号？",
        "orgCode": "001",
        "bizCode": "agents",
        "conversationId": "test-session-001"
    }
    """
    return await dispatcher.dispatch_stream(data, request)
@app.post("/api/chat/sync")
async def chat_sync(data: Dict = Body(...)):
    """
    同步对话接口（等待完整响应，适合测试）
    """
    result = await dispatcher.dispatch_sync(data)
    return JSONResponse(result)



# 启动

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True, # 开发模式：代码更新自动重启
        log_level="info",
    )