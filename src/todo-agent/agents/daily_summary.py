# agents/daily_summary.py
# 模式二：并行编排（Parallel）

# 场景：用户说"给我今日工作摘要"，需要同时查"今日待办"和"完成统计"

# 执行顺序
# get_today_todos --->
#                    |--> 两个同时查 -> LLM合并汇报               
# count_stats     --->

# 核心Python知识：asyncio.gather() ---多个协程并发运行

# 串行(慢): 先查A, 再查B, 共花 A+B 时间
# result_a = await query_a()
# result_b = await query_b()

# 并行(快)：A 和 B 同时查，共花 max(A, B) 时间
# result_a, result_b = await asyncio.gather(query_a(), query_b())

import asyncio
import json
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.abstract_tool import AbstractTool
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_MAX_TOKENS, logger
from db.todo_db import todo_db

class DailySummaryTool(AbstractTool):
    """
    并行编排示例：今日工作摘要

    并行执行(同时)：
    - 查询今日全部待办
    - 统计完成情况

    然后把两份数据合并，让LLM生成完整摘要

    关键点：两个查询互不依赖，并行执行节省时间
    """

    name = "daily_summary"
    description = "生成今日工作摘要，包含待办和完成统计"

    def __init__(self, handler = None):
        super().__init__(handler)
        self._llm = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0.7,
            max_tokens=LLM_MAX_TOKENS,
            streaming=True
        )

    async def _get_today_data(self):
        """获取今日待办 模拟IO操作"""
        todos = todo_db.list_today()
        return [
            {
                "标题": t.title,
                "截止": t.due_date or "无",
                "优先级": t.priority,
                "状态": "已完成" if t.done else "未完成",
            }
            for t in todos
        ]
    
    async def _get_stats_data(self):
        """获取整体统计信息"""
        all_todos = todo_db.list_all()
        total = len(all_todos)
        done = sum(1 for t in all_todos if t.done)
        today = todo_db.list_today()
        today_done = sum(1 for t in today if t.done)
        return {
            "总任务数": total,
            "已完成": done,
            "未完成": total - done,
            "今日任务数": len(today),
            "今日已完成": today_done,
        }
    
    async def arun(self, query: str, **kwargs) -> None:
        """
        并行执行两个数据查询
        asyncio.gather 让它们同时运行
        """

        today_todos, stats = await asyncio.gather(
            self._get_today_data(),
            self._get_stats_data()
        )
        # 把两个都完成后才继续往下执行
        today = datetime.now().strftime("%Y年%m月%d日")

        # 两份数据合并传给LLM生成摘要
        prompt = ChatPromptTemplate.from_template(
            "今天是{today}。\n\n"
            "今日待办事项：\n{todos_json}\n\n"
            "整体统计：\n{stats_json}\n\n"
            "用户问题:{query}\n\n"
            "请生成一份简洁的日志工作摘要"
            "包含重点任务摘要和完成进度，控制在150字以内"
        )

        chain = prompt | self._llm

        full_text = ""
        async for chunk in chain.astream({
            "today": today,
            "todos_json": json.dumps(today_todos, ensure_ascii=False),
            "stats_json": json.dumps(stats, ensure_ascii=False),
            "query": query
        }):
            token = chunk.content
            if token:
                full_text += token
                await self.handler.put_token(token=token)

        self.context.set_result_llm(full_text)
        await self.handler.put_data(
            biz_code=self.context.request_info.biz_code(),
            answer=full_text,
            data= today_todos,
        )


        

        
         