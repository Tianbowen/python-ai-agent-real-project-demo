"""
    LangChain流式调用
    安装：
    langchain-openai
    langchain-core
"""

import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# 定义LLM

llm = ChatOpenAI(
    base_url= "https://api.deepseek.com",
    api_key="", # 
    model= "deepseek-chat",
    streaming= True, # 关键：开启流式
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个Todo助手。"),
    ("human", "{query}")
])

chain = prompt | llm

async def main():
    # astream() 是异步流式迭代器，每次 yield 一个 token chunk
    async for chunk in chain.astream({"query": "介绍一下你自己"}):
        token = chunk.content
        if token:
            print(token, end="", flush=True) # 实时打印，不换行

asyncio.run(main())