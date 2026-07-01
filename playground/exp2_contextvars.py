# 即使3个请求交替执行，每个请求里current_user始终是自己的值，互不污染

import asyncio
from contextvars import ContextVar

# 类比：每个请求有自己独立的"用户信息盒子"
current_user: ContextVar[str] = ContextVar("current_user", default="未知")

async def handler_request(user_name: str, delay: float):
    """模拟处理一个HTTP请求"""
    # 设置当前请求的用户（只影响本协程，不影响其他协程）
    current_user.set(user_name)

    print(f"[{user_name}] 请求开始， current_user={current_user.get()}")
    await asyncio.sleep(delay) # 模拟IO等待， 期间其他协程在运行

    # 即使睡眠期间其他请求修改了 current_user, 这里仍然是自己的值
    print(f"[{user_name}] 请求结束, current_user={current_user.get()}") # 仍然正确

async def main():
    # 3个请求并发执行
    await asyncio.gather(
        handler_request('张三', 1.0),
        handler_request('李四', 0.5),
        handler_request('王五', 0.8),
    )

asyncio.run(main())
