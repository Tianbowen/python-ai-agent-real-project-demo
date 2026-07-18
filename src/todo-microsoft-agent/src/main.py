import asyncio
import os

from agent_framework import Agent, Message
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

from app.agent.tools import create_todo, list_todos, complete_todo, update_todo, delete_todo
# from app.repositories.memory_todo_repo import todo_repo
from app.dependencies import todo_service

async def run_with_approvals(
    agent: Agent,
    session,
    query: str,
):
    result = await agent.run(query, session=session)

    while result.user_input_requests:
        approval_messages: list[Message] = []

        for request in result.user_input_requests:
            function_call = request.function_call
            if function_call is None:
                continue

            print("\n===== 需要人工批准 =====")
            print(f"工具：{function_call.name}")
            print(f"参数：{function_call.arguments}")

            answer = await asyncio.to_thread(
                input,
                "是否批准？请输入 y 或 n：",
            )
            approved = answer.strip().lower() in {
                "y",
                "yes",
                "是",
                "确认",
                "同意",
            }

            approval_messages.append(
                Message(
                    role="user",
                    contents=[
                        request.to_function_approval_response(
                            approved=approved
                        )
                    ],
                )
            )

        if not approval_messages:
            raise RuntimeError("Agent 请求了用户输入，但没有可处理的工具审批")
        
        result = await agent.run(
            approval_messages,
            session=session,
        )

    return result

async def main() -> None:
    load_dotenv()

    client = OpenAIChatCompletionClient(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
        model=os.environ["OPENAI_CHAT_COMPLETION_MODEL"]
    )

    agent = Agent(
        client=client,
        name="TodoAssistant",
        instructions=(
            "你是一名待办事项助手。"
            "创建任务时调用create_todo工具。查询任务时调用 list_todos。"
            "完成任务时调用complete_todo。"
            "如果不知道待办ID，先调用list_todos查询，再调用complete_todo。"
            "修改任务时调用update_todo。"
            "如果用户没有提供待办ID，先调用list_todos找到目标。"
            "不能仅口头声称修改成功，必须以工具结果为准。"
            "删除任务时调用delete_todo。"
            "如果不知道待办ID，先调用list_todos查询。"
            "删除工具需要用户批准，不能绕过审批。"
            "用户说今天、明天或后天时，必须把相对日期原样传给工具，"
            "禁止自行猜测或换算具体年份。"
            "只能根据工具返回的数据回答，不能编造待办。"
            "始终用简体中文回复。"
        ),
        tools=[create_todo, list_todos, complete_todo, update_todo, delete_todo],
    )

    # 关键会话：后续 run 都传同一个 session
    # AgentSession 同一会话里保留对话上下文；不传session，每轮几乎是失忆的。
    session = agent.create_session()

    # turns = [
    #     "帮我创建一个待办：明天下午提交周报，优先级高",
    #     "我刚才创建了什么待办？请调用工具查一下。",
    #     "再加一个：后天买咖啡，优先级低",
    #     "现在一共有几条待办？列出标题和截止日期。",
    #     "把提交周报标记为已完成。",
    #     "列出所有已完成的待办。",
    #     "把买咖啡的标题改成购买咖啡豆，优先级改成high",
    #     "查询标题包含咖啡的待办",
    #     "删除标题包含咖啡的待办",
    #     "列出剩余待办",
    # ]

    # for i, query in enumerate(turns, start=1):
    #     print(f"\n===== 第 {i} 轮 =====")
    #     print(f"用户: {query}")
    #     # response = await agent.run(query, session=session)
    #     response = await run_with_approvals(agent=agent, session=session, query=query)
    #     print(f"助手：{response.text}")
    
    # print("\n===== 最终内存数据 =====")
    # for item in todo_service.list_todos():
    #     print(
    #         f"- [{item.priority.value}/{item.status.value}] "
    #         f"{item.title} (due={item.due_date}, id={item.id})"
    #     )

    todo = todo_service.create("审批测试任务")
    query = (
        f"请删除 ID 为 {todo.id} 的待办事项。"
        "必须调用 delete_todo 工具，不要只用文字回复。"
    )
    print(f"测试待办 ID：{todo.id}")
    print(f"调用前次数：{delete_todo.invocation_count}")
    response = await run_with_approvals(
        agent=agent,
        session=session,
        query=query,
    )
    print(f"审批请求处理后的回复：{response.text}")
    print(f"调用后次数：{delete_todo.invocation_count}")
    print(f"待办仍然存在：{todo_service.get(todo.id)}")

if __name__ == "__main__":
    asyncio.run(main())