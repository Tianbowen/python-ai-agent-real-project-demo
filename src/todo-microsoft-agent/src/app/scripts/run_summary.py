# 临时 先用 CLI验证

import asyncio
from app.workflows.today_summary import SummaryInput, today_summary_workflow
from app.dependencies import todo_service

async def main() -> None:
    todo_service.create("提交周报", priority="high", due_date='今天')
    todo_service.create("买咖啡", priority="low", due_date='明天')

    result = await today_summary_workflow.run(SummaryInput())
    print("State:", result.get_final_state())
    print("Output:", result.get_outputs()[0])

if __name__ == "__main__":
    asyncio.run(main())