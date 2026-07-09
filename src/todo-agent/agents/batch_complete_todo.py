# agents/batch_complete_todo.py
# 编排工具
# 模式一：流水线编排

from agents.abstract_tool import AbstractTool
from db.todo_db import todo_db
from langchain_core.prompts import ChatMessagePromptTemplate
from langchain_openai import ChatOpenAI
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, logger

class BatchCompleteTodoTool(AbstractTool):
    """
    流水线编排示例：批量完成任务

    执行顺序（固定的，写死的）：
    Step 1 -> 查询符合条件的任务列表
    Step 2 -> 循环逐条标记完成（每完成一条就推送给用户）
    Step 3 -> 汇总结果

    关键点：每一步的输入来自上一步的输出
    """

    name: "batch_complete_todo"
    description: "批量完成符合条件的多个任务"

    def __init__(self, handler = None):
        super().__init__(handler)
        self._llm = ChatOpenAI(
            base_url=LLM_API_BASE,
            api_key=LLM_API_KEY,
            model=LLM_MODEL_NAME,
            temperature=0.7,
            max_tokens=100,
            streaming=True,
        )

    async def arun(self, query: str, **kwargs) -> None:
        # 步骤1：查询目标任务（筛选条件）
        priority = self.context.ctx.slot_value("priority") if self.context.ctx else None
        all_todos = todo_db.list_all()

        # 只获取未完成的，如果指定了优先级则进一步筛选
        targets = [
            t for t in all_todos
            if not t.done and (priority is None or t.priority == priority)
        ]

        label = f"{priority}优先级:" if priority else "所有"

        # 没有目标任务 -> 直接结束，不进入循环
        if not targets:
            msg = f"没有找到{label}未完成的任务"
            await self.handler.put_token(msg)
            self.context.set_result_llm(msg)
            await self.handler.put_data(
                biz_code=self.context.request_info.biz_code(),
                answer=msg,
                data=[]
            )
            return

        # 步骤2：逐条完成(流水线核心)
        await self.handler.put_token(f"开始完成{label} {len(targets)} 条任务: \n")

        completed = []
        for todo in targets:
            # 调用 DB 操作
            item = todo_db.complete(todo.title)
            if item:
                completed.append(item)
                # 实时推送每条完成状态（流水线的体现）
                await self.handler.put_token(f"✅ {item.title}")

        # 步骤3：汇总(依赖 步骤2 的结果)
        summary = f"\n共完成{len(completed)} / {len(targets)} 条任务"
        await self.handler.put_token(summary)

        full_text = {
            f"开始完成{label} {len(targets)} 条任务: \n"
            + "\n".join("f✅ {i.title}" for i in completed)
            + summary
        }
        self.context.set_result_llm(full_text)
        await self.handler.put_data(
            biz_code=self.context.request_info.biz_code(),
            answer=full_text,
            data=[{"标题": i.title, "状态": "已完成"} for i in completed],
        )
