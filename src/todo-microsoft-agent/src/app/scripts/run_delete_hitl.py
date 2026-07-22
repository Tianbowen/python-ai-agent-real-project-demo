# scripts/run_delete_hitl.py

import asyncio

from agent_framework import WorkflowRunState

from app.dependencies import todo_service
from app.workflows.delete_todo_hitl import DeleteTodoInput, delete_todo_hitl_workflow

async def main() -> None:
    # 准备测试数据
    item = todo_service.create(title="HITL 删除演示", priority="low")
    print(f"已创建：id={item.id} | 标题={item.title}\n")

    # Phase 1：触发工作流，挂起等待确认
    r1 = await delete_todo_hitl_workflow.run(DeleteTodoInput(todo_id=item.id))

    print("Phase 1 状态：", r1.get_final_state())
    assert r1.get_final_state() == WorkflowRunState.IDLE_WITH_PENDING_REQUESTS

    for evt in r1.get_request_info_events():
        print(f"    待确认 -> request_id={evt.request_id}, data={evt.data}")

    # Phase 2：拒绝删除
    r2 = await delete_todo_hitl_workflow.run(responses={"delete_confirm": False})
    result2: object = r2.get_outputs()[0]
    print("Phase 2a 结果：", result2)
    assert result2.action == "cancelled"
    assert todo_service.get(item.id).title == "HITL 删除演示" # 待办仍存在
    print("√ 拒绝后待办仍存在")

    # Phase 3：重新挂起，这次同意删除
    print("\n--- 重新确认，同意删除 ---")
    r3 = await delete_todo_hitl_workflow.run(DeleteTodoInput(todo_id=item.id))
    assert r3.get_final_state() == WorkflowRunState.IDLE_WITH_PENDING_REQUESTS

    r4 = await delete_todo_hitl_workflow.run(responses={"delete_confirm": True})
    result4: object = r4.get_outputs()[0]
    print("Phase 3 结果：", result4)
    assert result4.action == "deleted"

    remaining_ids = [t.id for t in todo_service.list_todos()]
    assert item.id not in remaining_ids
    print("✓ 同意后待办已删除，剩余 id:", remaining_ids)

if __name__ == "__main__":
    asyncio.run(main())