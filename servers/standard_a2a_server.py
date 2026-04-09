"""
标准A2A服务器 - 不包含A2X能量经济扩展
用于与A2X扩展服务器进行对比测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from a2a.server.apps import A2AStarletteApplication
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore
    from a2a.types import AgentCard, AgentCapabilities, AgentSkill, TextPart, Message
except ImportError:
    print("Error: a2a not installed. Run: py -m pip install a2a-sdk")
    sys.exit(1)


class StandardAgentExecutor:
    """标准A2A智能体执行器 - 无能量经济逻辑"""

    async def execute(self, context, event_queue):
        """执行任务 - 无论任务价值高低都处理"""
        message = context.message
        input_text = ""
        if message.parts:
            for part in message.parts:
                if isinstance(part, TextPart):
                    input_text = part.text
                    break
        return f"Standard A2A processed: {input_text[:50]}"


class StandardRequestHandler(DefaultRequestHandler):
    """标准请求处理器"""

    def __init__(self):
        super().__init__(
            agent_executor=StandardAgentExecutor(),
            task_store=InMemoryTaskStore()
        )


def create_standard_agent_card() -> AgentCard:
    """创建标准A2A AgentCard"""
    return AgentCard(
        agentId="standard-a2a-agent",
        name="Standard A2A Agent",
        description="Standard A2A agent without energy economy",
        url="http://localhost:8001/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(
            streaming=True,
            pushNotifications=False
        ),
        skills=[
            AgentSkill(
                id="standard_task",
                name="Standard Task Processing",
                description="Processes any task without discrimination",
                tags=["standard", "basic"],
                examples=["any task"]
            )
        ]
    )


def create_app() -> A2AStarletteApplication:
    """创建A2A应用"""
    agent_card = create_standard_agent_card()
    request_handler = StandardRequestHandler()

    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )


def run_server(port: int = 8001):
    """运行标准A2A服务器"""
    app = create_app()
    print(f"Starting Standard A2A Server on port {port}...")
    
    import uvicorn
    uvicorn.run(app.build(), host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    run_server(8001)