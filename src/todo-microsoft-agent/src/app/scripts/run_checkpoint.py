# scripts/run_checkpoint.py

"""
演示 FileCheckpointStorage：
    Phase 1 - 触发 HITL 挂起，保存 checkpoint 到磁盘，打印 checkpoint_id 后退出。
    Phase 2 - 用 checkpoint_id 恢复，传入确认结果，完成删除。
"""

import asyncio
import sys
from pathlib import Path

from agent_framework import FileCheckpointStorage, WorkflowRunState

from app.dependencies import todo_service
from app.workflows.delete_todo_hitl import DeleteTodoInput, delete_todo_hitl_workflow

# 所有 checkpoint 文件存在这里
CHECKPOINT_DIR = Path(__file__).parent.parent.parent / "checkpoints"

storage = FileCheckpointStorage(
    CHECKPOINT_DIR,
    allowed_checkpoint_types=[
        "app.workflows.delete_todo_hitl:DeleteTodoInput",
        "app.workflows.delete_todo_hitl:DeleteTodoResult",
    ],
)

async def phase1() -> None:
    """创建待办，触发 HITL，保存 checkpoint。"""
    item = todo_service.create(title="Checkpoint 演示", priority="medium")
    print(f"已创建待办：id={item.id} | 标题={item.title}")

    r = await delete_todo_hitl_workflow.run(
        DeleteTodoInput(todo_id=item.id),
        checkpoint_storage=storage,
    )
    assert r.get_final_state() == WorkflowRunState.IDLE_WITH_PENDING_REQUESTS

    # 从存储里拿到刚保存的 checkpoint
    checkpoints = await storage.list_checkpoints(
        workflow_name=delete_todo_hitl_workflow.name
    )
    cp = checkpoints[-1]
    print(f"\nPhase 1 完成, checkpoint_id={cp.checkpoint_id}")
    print("请把上面的 checkpoint_id 复制，然后运行：")
    print(f" uv run python -m app.scripts.run_checkpoint phase2 <checkpoint_id>")

async def phase2(checkpoint_id: str) -> None:
    """用 checkpoint_id 恢复，同意删除。"""
    print(f"用 checkpoint_id={checkpoint_id} 恢复工作流...")

    r = await delete_todo_hitl_workflow.run(
        checkpoint_id=checkpoint_id,
        response={"delete_confirm": True},
        checkpoint_storage=storage,
    )
    print("恢复后状态：", r.get_final_state())
    result = r.get_outputs()[0]
    print("执行结果:", result)

async def same_process_dome() -> None:
    """同进程提示：InMemoryCheckpointStorage，数据不会消失。"""
    mem_storage = af.InMemoryCheckpointStorage() if False else None

    from agent_framework import InMemoryCheckpointStorage
    mem_storage = InMemoryCheckpointStorage()

    item = todo_service.create(title="同进程 Checkpoint 演示", priority="low")
    print(f"已创建：id={item.id}")

    r1 = await delete_todo_hitl_workflow.run(
        DeleteTodoInput(todo_id=item.id),
        checkpoint_storage=mem_storage,
    )
    cps = await mem_storage.list_checkpoints(workflow_name=delete_todo_hitl_workflow.name)
    cp_id = cps[-1].checkpoint_id
    print(f"Phase 1 状态: {r1.get_final_state()}, checkpoint_id={cp_id}")

    r2 = await delete_todo_hitl_workflow.run(
        checkpoint_id=cp_id,
        responses={"delete_confirm": True},
        checkpoint_storage=mem_storage,
    )
    print(f"Phase 2 状态：{r2.get_final_state()}, 结果：{r2.get_outputs()[0]}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        asyncio.run(phase1())
    elif sys.argv[1] == "phase2" and len(sys.argv) == 3:
        asyncio.run(phase2(sys.argv[2]))
    elif len(sys.argv) == 2 and sys.argv[1] == "demo":
        asyncio.run(same_process_dome())
    else:
        print("用法：")
        print(" uv run python -m app.scripts.run_checkpoint #Phase 1")
        print(" uv run python -m app.scripts.run_checkpoint phase2 <id> # Phase 2")