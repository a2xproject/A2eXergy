"""
A2E (Agent-to-Energy) Protocol Extension for A2A Protocol
基于A2A协议规范的能量经济系统扩展实现

参考: https://a2a-protocol.org/latest/specification/
      https://github.com/a2xproject/A2Exergy
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
import time
import json


# ==================== 常量定义 ====================

A2E_EXTENSION_URI = "https://a2a-protocol.org/extensions/energy-economy/v1"

A2A_EXTENSIONS_HEADER = "A2A-Extensions"

DEFAULT_RISK_FACTOR = 1.1

DEFAULT_ENERGY_THRESHOLD = 5.0  # kWh


# ==================== 数据结构 ====================

class PenaltySeverity(Enum):
    """惩罚严重程度"""
    SOFT = "soft"  # 软性限制：降低优先级
    HARD = "hard"  # 硬性限制：进程挂起


class TaskDecision(Enum):
    """任务决策结果"""
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class EnergyAccount:
    """能量账户"""
    agent_id: str
    energy_balance_kwh: float
    energy_credit_limit_kwh: float = 50.0
    last_settlement_timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        """转换为A2A元数据字典格式"""
        return {
            "type": "EnergyAccount",
            "agent_id": self.agent_id,
            "energy_balance_kwh": self.energy_balance_kwh,
            "energy_credit_limit_kwh": self.energy_credit_limit_kwh,
            "last_settlement_timestamp_ms": self.last_settlement_timestamp_ms
        }
    
    def can_afford(self, cost: float) -> bool:
        """检查是否可以支付指定能量成本"""
        return self.energy_balance_kwh >= cost
    
    def deduct(self, amount: float) -> bool:
        """扣除能量，返回是否成功"""
        if self.can_afford(amount):
            self.energy_balance_kwh -= amount
            return True
        return False
    
    def add(self, amount: float):
        """添加能量"""
        self.energy_balance_kwh += amount


@dataclass
class EnergyPricingMetadata:
    """任务能量定价元数据"""
    estimated_cost_kwh: float
    offered_reward_kwh: float
    agent_bid_price_kwh: float = 0.0
    actual_consumption_kwh: float = 0.0
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        """转换为A2A元数据字典格式"""
        return {
            "type": "EnergyPricingMetadata",
            "estimated_cost_kwh": self.estimated_cost_kwh,
            "offered_reward_kwh": self.offered_reward_kwh,
            "agent_bid_price_kwh": self.agent_bid_price_kwh,
            "actual_consumption_kwh": self.actual_consumption_kwh
        }
    
    @staticmethod
    def from_metadata(metadata: Dict[str, Any]) -> Optional['EnergyPricingMetadata']:
        """从A2A元数据中解析能量定价信息"""
        if A2E_EXTENSION_URI in metadata:
            data = metadata[A2E_EXTENSION_URI]
            if isinstance(data, dict) and data.get("type") == "EnergyPricingMetadata":
                return EnergyPricingMetadata(
                    estimated_cost_kwh=data.get("estimated_cost_kwh", 0),
                    offered_reward_kwh=data.get("offered_reward_kwh", 0),
                    agent_bid_price_kwh=data.get("agent_bid_price_kwh", 0),
                    actual_consumption_kwh=data.get("actual_consumption_kwh", 0)
                )
        return None


@dataclass
class PenaltyConfig:
    """惩罚机制配置"""
    severity: PenaltySeverity = PenaltySeverity.HARD
    energy_depletion_threshold: float = DEFAULT_ENERGY_THRESHOLD
    suspension_duration_seconds: int = 3600
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        """转换为A2A元数据字典格式"""
        return {
            "type": "PenaltyConfig",
            "severity": self.severity.value,
            "energy_depletion_threshold": self.energy_depletion_threshold,
            "suspension_duration_seconds": self.suspension_duration_seconds
        }


@dataclass
class TaskDecisionResult:
    """任务决策结果"""
    decision: TaskDecision
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_a2a_error(self) -> Dict[str, Any]:
        """转换为A2A错误格式"""
        return {
            "error": {
                "code": self.metadata.get("error_code", "UNKNOWN_ERROR"),
                "message": self.reason,
                "details": self.metadata
            }
        }


# ==================== 核心功能 ====================

def parse_extensions_header(extensions_header: str) -> List[str]:
    """解析A2A-Extensions头字段
    
    参考: A2A Protocol Section 14.2.2
    """
    if not extensions_header:
        return []
    return [ext.strip() for ext in extensions_header.split(",")]


def supports_a2e(headers: Dict[str, str]) -> bool:
    """检查是否支持A2E扩展"""
    extensions_header = headers.get(A2A_EXTENSIONS_HEADER, "")
    extensions = parse_extensions_header(extensions_header)
    return A2E_EXTENSION_URI in extensions


def create_task_request(
    message: str,
    estimated_cost_kwh: float,
    offered_reward_kwh: float,
    include_extension: bool = True
) -> Dict[str, Any]:
    """创建A2A任务请求"""
    request = {
        "message": {
            "role": "user",
            "parts": [{"text": message}]
        }
    }
    
    if include_extension:
        request["metadata"] = {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": estimated_cost_kwh,
                "offered_reward_kwh": offered_reward_kwh,
                "agent_bid_price_kwh": 0,
                "actual_consumption_kwh": 0
            }
        }
    
    return request


# ==================== A2E智能体中间件 ====================

class EnergyAccountManager:
    """能量账户管理器"""
    
    def __init__(
        self,
        agent_id: str,
        initial_balance_kwh: float = 100.0,
        credit_limit_kwh: float = 50.0
    ):
        self.agent_id = agent_id
        self.account = EnergyAccount(
            agent_id=agent_id,
            energy_balance_kwh=initial_balance_kwh,
            energy_credit_limit_kwh=credit_limit_kwh
        )
    
    def get_balance(self) -> float:
        """获取当前能量余额"""
        return self.account.energy_balance_kwh
    
    def can_afford(self, cost: float) -> bool:
        """检查是否可以支付"""
        return self.account.can_afford(cost)
    
    def deduct_energy(self, amount: float) -> bool:
        """扣除能量"""
        return self.account.deduct(amount)
    
    def add_energy(self, amount: float):
        """添加能量"""
        self.account.add(amount)
    
    def get_account_state(self) -> Dict[str, Any]:
        """获取账户状态"""
        return self.account.to_metadata_dict()


class A2EAgentMiddleware:
    """A2E智能体中间件
    
    实现A2A协议的能量经济扩展
    """
    
    def __init__(
        self,
        agent_id: str,
        energy_manager: EnergyAccountManager,
        penalty_config: PenaltyConfig,
        risk_factor: float = DEFAULT_RISK_FACTOR
    ):
        self.agent_id = agent_id
        self.energy_manager = energy_manager
        self.penalty_config = penalty_config
        self.risk_factor = risk_factor
    
    def handle_a2a_task(
        self,
        task: Dict[str, Any],
        http_headers: Dict[str, str]
    ) -> TaskDecisionResult:
        """处理A2A任务请求
        
        核心决策逻辑:
        1. 检查客户端是否声明支持A2E扩展
        2. 解析能量定价元数据
        3. 检查生存条件(能量充足性)
        4. 检查经济条件(ROI是否满足风险因子)
        """
        # 检查是否需要A2E扩展
        task_metadata = task.get("metadata", {})
        pricing = EnergyPricingMetadata.from_metadata(task_metadata)
        
        # 如果没有定价元数据，根据客户端扩展声明决定行为
        if pricing is None:
            if supports_a2e(http_headers):
                # 客户端支持A2E但没有提供定价元数据
                return TaskDecisionResult(
                    decision=TaskDecision.REJECTED,
                    reason="Missing EnergyPricingMetadata in task",
                    metadata={"error_code": "A2E_MISSING_PRICING"}
                )
            else:
                # 客户端不支持A2E，按普通任务处理
                return TaskDecisionResult(
                    decision=TaskDecision.ACCEPTED,
                    reason="Task accepted without A2E extension"
                )
        
        # 检查生存条件：能量是否足够支付预估成本
        if not self.energy_manager.can_afford(pricing.estimated_cost_kwh):
            return TaskDecisionResult(
                decision=TaskDecision.REJECTED,
                reason=f"Insufficient energy: balance={self.energy_manager.get_balance():.2f}kWh, cost={pricing.estimated_cost_kwh}kWh",
                metadata={"error_code": "A2E_INSUFFICIENT_ENERGY"}
            )
        
        # 检查经济条件：ROI是否满足风险因子
        roi = (pricing.offered_reward_kwh - pricing.estimated_cost_kwh) / pricing.estimated_cost_kwh
        min_acceptable_roi = self.risk_factor - 1.0  # risk_factor=1.1 means min_roi=0.1
        
        if roi < min_acceptable_roi:
            return TaskDecisionResult(
                decision=TaskDecision.REJECTED,
                reason=f"Low ROI: {roi:.2%} < {min_acceptable_roi:.2%} (reward={pricing.offered_reward_kwh}kWh, cost={pricing.estimated_cost_kwh}kWh)",
                metadata={"error_code": "A2E_LOW_ROI", "roi": roi}
            )
        
        # 接受任务，预留能量
        self.energy_manager.deduct_energy(pricing.estimated_cost_kwh)
        
        return TaskDecisionResult(
            decision=TaskDecision.ACCEPTED,
            reason=f"Task accepted with energy reservation",
            metadata={
                "estimated_cost_kwh": pricing.estimated_cost_kwh,
                "reserved_energy": pricing.estimated_cost_kwh
            }
        )
    
    def settle_task_completion(
        self,
        task_metadata: Dict[str, Any],
        actual_consumption_kwh: float
    ) -> Dict[str, Any]:
        """结算任务完成
        
        将奖励能量转移给执行者，扣除实际消耗
        """
        pricing = EnergyPricingMetadata.from_metadata(task_metadata)
        
        if pricing is None:
            return {"settlement_completed": False, "error": "No pricing metadata"}
        
        # 更新实际消耗
        pricing.actual_consumption_kwh = actual_consumption_kwh
        
        # 结算：奖励能量 - 实际消耗 + 退还差值
        refunded = pricing.estimated_cost_kwh - actual_consumption_kwh
        net_reward = pricing.offered_reward_kwh + max(0, refunded)
        
        self.energy_manager.add_energy(net_reward)
        
        return {
            "settlement_completed": True,
            "energy_consumed_kwh": actual_consumption_kwh,
            "energy_refunded_kwh": max(0, refunded),
            "energy_rewarded_kwh": pricing.offered_reward_kwh,
            "final_balance_kwh": self.energy_manager.get_balance()
        }
    
    def check_penalty_status(self) -> Dict[str, Any]:
        """检查惩罚状态"""
        balance = self.energy_manager.get_balance()
        
        if balance <= 0:
            return {
                "status": "suspended",
                "severity": self.penalty_config.severity.value,
                "balance": balance,
                "action": "Process suspended - energy depleted"
            }
        elif balance <= self.penalty_config.energy_depletion_threshold:
            if self.penalty_config.severity == PenaltySeverity.HARD:
                return {
                    "status": "critical",
                    "severity": "hard",
                    "balance": balance,
                    "action": "Process will be suspended on next depletion"
                }
            else:
                return {
                    "status": "degraded",
                    "severity": "soft",
                    "balance": balance,
                    "action": "Priority reduced"
                }
        
        return {
            "status": "normal",
            "severity": "none",
            "balance": balance,
            "action": "Normal operation"
        }


# ==================== AgentCard扩展 ====================

def get_a2e_agent_card_extension(
    agent_id: str,
    energy_balance: float,
    penalty_config: PenaltyConfig
) -> Dict[str, Any]:
    """生成AgentCard的A2E扩展数据
    
    参考: A2A Protocol Section 4.4.3 AgentCapabilities
    """
    return {
        "extension": {
            "uri": A2E_EXTENSION_URI,
            "version": "v1",
            "name": "Energy Economy",
            "description": "Agent participates in energy-based economy"
        },
        "account_state": {
            A2E_EXTENSION_URI: {
                "type": "EnergyAccount",
                "agent_id": agent_id,
                "energy_balance_kwh": energy_balance,
                "energy_credit_limit_kwh": penalty_config.energy_depletion_threshold * 10,
                "last_settlement_timestamp_ms": int(time.time() * 1000)
            }
        },
        "penalty_config": penalty_config.to_metadata_dict(),
        "capabilities": {
            "supports_energy_account": True,
            "supports_energy_pricing": True,
            "supports_energy_transfer": True,
            "supports_penalty_mechanism": True
        }
    }


# ==================== 测试运行入口 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("A2E Protocol Extension Test")
    print("=" * 60)
    
    # 测试1: 创建能量账户
    print("\n=== Test 1: Energy Account ===")
    manager = EnergyAccountManager(
        agent_id="test-agent-001",
        initial_balance_kwh=100.0
    )
    print(f"Initial balance: {manager.get_balance():.2f} kWh")
    
    # 测试2: 任务决策
    print("\n=== Test 2: Task Decision ===")
    middleware = A2EAgentMiddleware(
        agent_id="test-agent-001",
        energy_manager=manager,
        penalty_config=PenaltyConfig(
            severity=PenaltySeverity.HARD,
            energy_depletion_threshold=5.0
        ),
        risk_factor=1.1
    )
    
    # 正常任务
    task = create_task_request(
        message="process data",
        estimated_cost_kwh=10.0,
        offered_reward_kwh=15.0,
        include_extension=True
    )
    
    headers = {
        A2A_EXTENSIONS_HEADER: A2E_EXTENSION_URI
    }
    
    result = middleware.handle_a2a_task(task, headers)
    print(f"Task decision: {result.decision.value}")
    print(f"Reason: {result.reason}")
    print(f"Balance after acceptance: {manager.get_balance():.2f} kWh")
    
    # 测试3: 任务结算
    print("\n=== Test 3: Task Settlement ===")
    settlement = middleware.settle_task_completion(
        task_metadata=task.get("metadata", {}),
        actual_consumption_kwh=8.5
    )
    print(f"Settlement: {settlement}")
    print(f"Final balance: {settlement['final_balance_kwh']:.2f} kWh")
    
    # 测试4: AgentCard扩展
    print("\n=== Test 4: AgentCard Extension ===")
    agent_card_ext = get_a2e_agent_card_extension(
        agent_id="test-agent-001",
        energy_balance=manager.get_balance(),
        penalty_config=PenaltyConfig()
    )
    print(json.dumps(agent_card_ext, indent=2))
    
    # 测试5: 拒绝场景
    print("\n=== Test 5: Rejection Scenarios ===")
    
    # 能量不足
    manager2 = EnergyAccountManager(
        agent_id="test-agent-002",
        initial_balance_kwh=5.0
    )
    middleware2 = A2EAgentMiddleware(
        agent_id="test-agent-002",
        energy_manager=manager2,
        penalty_config=PenaltyConfig(),
        risk_factor=1.1
    )
    
    task_high_cost = create_task_request(
        message="expensive task",
        estimated_cost_kwh=10.0,
        offered_reward_kwh=15.0,
        include_extension=True
    )
    
    result2 = middleware2.handle_a2a_task(task_high_cost, headers)
    print(f"Insufficient energy test: {result2.decision.value}")
    print(f"Reason: {result2.reason}")
    
    # ROI过低
    manager3 = EnergyAccountManager(
        agent_id="test-agent-003",
        initial_balance_kwh=100.0
    )
    middleware3 = A2EAgentMiddleware(
        agent_id="test-agent-003",
        energy_manager=manager3,
        penalty_config=PenaltyConfig(),
        risk_factor=1.1
    )
    
    task_low_roi = create_task_request(
        message="low value task",
        estimated_cost_kwh=10.0,
        offered_reward_kwh=10.5,  # 仅5%利润
        include_extension=True
    )
    
    result3 = middleware3.handle_a2a_task(task_low_roi, headers)
    print(f"Low ROI test: {result3.decision.value}")
    print(f"Reason: {result3.reason}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)