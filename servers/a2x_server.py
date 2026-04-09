"""
A2X扩展服务器 - 包含能量经济逻辑
用于与标准A2A服务器进行对比测试
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests"))

try:
    from a2a.server.apps import A2AStarletteApplication
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore
    from a2a.types import AgentCard, AgentCapabilities, AgentSkill, TextPart, Message
    import uvicorn
except ImportError:
    print("Error: a2a not installed. Run: py -m pip install a2a-sdk")
    sys.exit(1)

try:
    from a2e_protocol_extension import (
        A2EAgentMiddleware,
        EnergyAccountManager,
        PenaltyConfig,
        PenaltySeverity,
        A2E_EXTENSION_URI,
        EnergyPricingMetadata,
        TaskDecision,
    )
except ImportError as e:
    print(f"Warning: Could not import A2X extension: {e}")
    sys.exit(1)


class A2XRequestHandler(DefaultRequestHandler):
    """A2X请求处理器"""

    def __init__(self, initial_energy: float = 100.0):
        self.energy_manager = EnergyAccountManager(
            agent_id="a2x-energy-agent",
            initial_balance_kwh=initial_energy
        )
        self.penalty_config = PenaltyConfig(
            severity=PenaltySeverity.HARD,
            energy_depletion_threshold=5.0
        )
        self.middleware = A2EAgentMiddleware(
            agent_id="a2x-energy-agent",
            energy_manager=self.energy_manager,
            penalty_config=self.penalty_config,
            risk_factor=1.1
        )
        self.tasks_completed = 0
        self.tasks_rejected = 0
        self.total_energy_used = 0.0
        self.total_reward_earned = 0.0
        
        super().__init__(
            agent_executor=None,
            task_store=InMemoryTaskStore()
        )

    async def on_message_send(self, params, context=None):
        """处理A2A消息请求 - 带能量经济决策"""
        http_headers = {}
        if context and hasattr(context, 'headers'):
            http_headers = {k.lower(): v for k, v in dict(context.headers).items()}
        
        # 尝试多种方式获取metadata
        task_metadata = {}
        
        # 方法1: 直接从params获取
        if hasattr(params, 'metadata') and params.metadata:
            task_metadata = dict(params.metadata)
        
        # 方法2: 从message获取
        if not task_metadata and hasattr(params, 'message'):
            message = params.message
            if hasattr(message, 'metadata') and message.metadata:
                task_metadata = dict(message.metadata)
        
        # 方法3: 检查原始params字典形式
        if not task_metadata and hasattr(params, '_params'):
            raw_params = params._params
            if 'metadata' in raw_params:
                task_metadata = dict(raw_params['metadata'])
        
        # Debug: 打印最终获取到的metadata
        print(f"[A2X] task_metadata keys: {list(task_metadata.keys())}")
        print(f"[A2X] http_headers: {http_headers}")
        
        # 尝试从metadata中找A2E扩展
        a2e_key = "https://a2a-protocol.org/extensions/energy-economy/v1"
        pricing = None
        if a2e_key in task_metadata:
            a2e_data = task_metadata[a2e_key]
            pricing = EnergyPricingMetadata(
                estimated_cost_kwh=a2e_data.get("estimated_cost_kwh", 0),
                offered_reward_kwh=a2e_data.get("offered_reward_kwh", 0),
                agent_bid_price_kwh=a2e_data.get("agent_bid_price_kwh", 0),
                actual_consumption_kwh=a2e_data.get("actual_consumption_kwh", 0)
            )
        
        if pricing:
            # 有能量定价，使用A2X决策
            task_dict = {"metadata": task_metadata}
            result = self.middleware.handle_a2a_task(task_dict, http_headers)
            
            if result.decision == TaskDecision.REJECTED:
                self.tasks_rejected += 1
                print(f"[A2X] REJECTED: {result.reason}")
                return Message(
                    message_id="msg-rejected",
                    role="agent",
                    parts=[TextPart(text=f"Task rejected: {result.reason}")]
                )
            
            # 任务被接受
            actual_consumption = pricing.estimated_cost_kwh * 0.85
            settlement = self.middleware.settle_task_completion(
                task_metadata=task_metadata,
                actual_consumption_kwh=actual_consumption
            )
            
            self.tasks_completed += 1
            self.total_energy_used += actual_consumption
            self.total_reward_earned += pricing.offered_reward_kwh
            
            print(f"[A2X] ACCEPTED: ROI={((pricing.offered_reward_kwh-pricing.estimated_cost_kwh)/pricing.estimated_cost_kwh):.1%}, Energy={self.energy_manager.get_balance():.2f} kWh")
            
            return Message(
                message_id="msg-completed",
                role="agent",
                parts=[TextPart(text=f"A2X processed: Energy={self.energy_manager.get_balance():.2f} kWh")]
            )
        else:
            print(f"[A2X] No pricing metadata - accepting task by default (metadata keys: {list(task_metadata.keys())})")
            return Message(
                message_id="msg-nometadata",
                role="agent",
                parts=[TextPart(text="A2X processed (no metadata)")]
            )

    def get_stats(self):
        return {
            "tasks_completed": self.tasks_completed,
            "tasks_rejected": self.tasks_rejected,
            "total_energy_used": self.total_energy_used,
            "total_reward_earned": self.total_reward_earned,
            "current_energy": self.energy_manager.get_balance(),
            "efficiency": self.total_reward_earned / max(self.total_energy_used, 0.001)
        }


def create_a2x_agent_card() -> AgentCard:
    """创建A2X扩展AgentCard"""
    return AgentCard(
        agentId="a2x-energy-agent",
        name="A2X Energy Economy Agent",
        description="A2A agent with A2X energy economy extension",
        url="http://localhost:8002/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(
            streaming=True,
            pushNotifications=False
        ),
        skills=[
            AgentSkill(
                id="a2x_energy_task",
                name="A2X Energy Economy Task",
                description="Task with energy-based economic decision making",
                tags=["a2x", "energy", "economy"],
                examples=["task with energy pricing"]
            )
        ]
    )


def create_app() -> A2AStarletteApplication:
    """创建A2X应用"""
    agent_card = create_a2x_agent_card()
    request_handler = A2XRequestHandler()

    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )


def run_server(port: int = 8002, initial_energy: float = 100.0):
    """运行A2X服务器"""
    app = create_app()
    
    print(f"Starting A2X Server on port {port}...")
    print(f"Initial energy: {initial_energy} kWh")
    
    uvicorn.run(app.build(), host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    run_server(8002, 100.0)