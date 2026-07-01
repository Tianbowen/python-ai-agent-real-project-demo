# 整个流式输出的核心机制

import asyncio

async def producer(queue: asyncio.Queue):
    """模拟 LLM 逐字生成"""
    words = ["今","天", "天", "气", "不", "错"]
    for word in words:
        await asyncio.sleep(0.3) # 模拟 LLM 生成延迟
        await queue.put(word) # 放入队列
        print(f"[生产者] 放入[{word}]")
    await queue.put(None)

async def consumer(queue: asyncio.Queue):
    """模拟 SSE 推送给客户端 """
    while True:
        word = await queue.get() # 取出
        if word is None:
            print("[消费者] 收到结束信号，停止")
            break
        print(f"消费者 推给客户端:{word}")

async def main():
    queue = asyncio.Queue()
    await asyncio.gather(producer(queue), 
                         consumer(queue),
    )

asyncio.run(main())