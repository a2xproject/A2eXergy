# A2E Protocol Extension for A2A
## Agent-to-Energy: A2A Protocol Extension v1

一个符合A2A协议规范的能量经济系统扩展实现。

---

## 概述

A2E (Agent-to-Energy) 是 A2A 协议的官方扩展，旨在将物理能量消耗作为智能体经济系统的刚性锚点。本实现严格遵循 A2A 协议规范（Section 4.6 Extensions），通过标准化的扩展机制实现能量账本管理、动态定价和生存惩罚机制。

### 关键特性

✅ **完全符合 A2A 规范**
- 使用标准 URI 标识符: `https://a2a-protocol.org/extensions/energy-economy/v1`
- 正确实现 `A2A-Extensions` HTTP 头机制
- 遵循 A2A 元数据结构规范 (Section 3.2.5)
- 集成到 AgentCard.capabilities (Section 4.4.3)

✅ **最小侵入设计**
- 作为扩展层叠加在现有 A2A 通信之上
- 与 A2A Python SDK 完全兼容
- 不修改 A2A 核心操作

✅ **版本化和兼容性**
- 扩展 URI 包含版本信息 (`/v1`)
- 支持扩展版本协商
- 向后兼容非 A2E 任务

✅ **生存驱动经济模型**
- 智能体必须通过服务赚取能量来维持运行
- 动态定价机制
- 资源约束下的理性决策

---

## A2A 规范符合性说明

### 1. 扩展声明 (Section 4.6.1 Extension Declaration)

```python
A2E_EXTENSION_URI = "https://a2a-protocol.org/extensions/energy-economy/v1"

def get_a2e_extensions_header() -> str:
    """返回 A2A-Extensions 头值"""
    return A2E_EXTENSION_URI
```

**符合性检查：**
- ✅ 扩展使用唯一 URI 标识
- ✅ URI 包含版本信息 (`/v1`)
- ✅ 支持通过 A2A-Extensions HTTP 头声明扩展使用

### 2. HTTP 头机制 (Section 14.2.2 A2A-Extensions Header)

```python
A2A_EXTENSIONS_HEADER = "A2A-Extensions"

def supports_a2e(headers: Dict[str, str]) -> bool:
    """检查 A2E 扩展是否受支持"""
    extensions_header = headers.get(A2A_EXTENSIONS_HEADER, "")
    extensions = parse_extensions_header(extensions_header)
    return A2E_EXTENSION_URI in extensions
```

**符合性检查：**
- ✅ 使用标准的 `A2A-Extensions` 头字段
- ✅ 正确解析逗号分隔的扩展 URI 列表
- ✅ 客户端通过 HTTP 头表明扩展使用意图

### 3. 元数据结构 (Section 3.2.5 Metadata)

A2A 规范允许扩展向 Message 和 Artifact 贡献元数据。A2E 使用以下结构：

```python
@dataclass
class EnergyPricingMetadata:
    """任务能量定价元数据"""
    estimated_cost_kwh: float
    offered_reward_kwh: float
    agent_bid_price_kwh: float
    actual_consumption_kwh: float
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        """转换为 A2A 元数据字典格式"""
        return {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": self.estimated_cost_kwh,
                ...
            }
        }
```

**符合性检查：**
- ✅ 扩展数据存储在 `metadata` 字典中
- ✅ 使用扩展 URI 作为顶级键
- ✅ 包含类型标识符用于结构化数据
- ✅ 与 A2A 消息格式兼容

### 4. AgentCard 扩展 (Section 4.4.1 AgentCard)

```python
def get_a2e_agent_card_extension(agent_id: str, 
                                energy_balance: float,
                                penalty_config: PenaltyConfig) -> Dict[str, Any]:
    """生成 AgentCard 的 A2E 扩展数据"""
    capability = EnergyEconomyCapability()
    account = EnergyAccount(...)
    
    return {
        "extension": {
            "uri": A2E_EXTENSION_URI,
            "version": capability.version,
            ...
        },
        "account_state": account.to_metadata_dict(),
        "penalty_config": penalty_config.to_metadata_dict()
    }
```

**符合性检查：**
- ✅ 扩展数据集成到 AgentCard 结构
- ✅ 在 capabilities 中声明扩展支持
- ✅ 包含扩展 URI 和版本信息

---

## 安装和使用

### 安装

```bash
# 无需额外依赖，仅使用 Python 标准库
cp a2e_protocol_extension.py your_agent_project/
```

### 基本使用

#### 1. 初始化能量账户管理器

```python
from a2e_protocol_extension import (
    EnergyAccountManager,
    PenaltyConfig,
    PenaltySeverity,
    A2EAgentMiddleware,
    A2E_EXTENSION_URI
)

# 创建能量账户
energy_manager = EnergyAccountManager(
    agent_id="agent-123",
    initial_balance_kwh=100.0,
    credit_limit_kwh=50.0
)

# 配置惩罚策略
penalty_config = PenaltyConfig(
    severity=PenaltySeverity.HARD,
    energy_depletion_threshold=5.0,
    suspension_duration_seconds=3600  # 1小时
)
```

#### 2. 初始化 A2E 中间件

```python
middleware = A2EAgentMiddleware(
    agent_id="agent-123",
    energy_manager=energy_manager,
    penalty_config=penalty_config,
    risk_factor=1.1  # ROI 安全边际
)
```

#### 3. 处理 A2A 任务请求

```python
def handle_a2a_task_request(task: Dict[str, Any], 
                          http_headers: Dict[str, str]):
    """
    A2A 任务请求处理器
    
    符合 A2A 规范: 客户端通过 A2A-Extensions 头声明扩展使用
    """
    # 检查任务是否包含 A2E 扩展
    result = middleware.handle_a2a_task(task, http_headers)
    
    if result.decision == TaskDecision.ACCEPTED:
        # 执行任务
        execute_task(task)
        
        # 结算能量消耗
        actual_consumption = measure_energy_consumption()
        settlement = middleware.settle_task_completion(
            task_metadata=task.get("metadata", {}),
            actual_consumption_kwh=actual_consumption
        )
        
        print(f"任务完成，结算: {settlement}")
    else:
        # 拒绝任务
        print(f"任务被拒绝: {result.reason}")
        # 返回 A2A 格式的错误响应
        return {
            "error": {
                "code": result.metadata.get("error_code"),
                "message": result.reason,
                "details": result.metadata
            }
        }
```

#### 4. 构建 A2A AgentCard

```python
from a2e_protocol_extension import get_a2e_agent_card_extension

# 生成包含 A2E 扩展的 AgentCard
agent_card = {
    "agentId": "agent-123",
    "name": "Energy-Aware Agent",
    "version": "1.0.0",
    "description": "Agent participating in energy economy",
    "capabilities": [
        get_a2e_agent_card_extension(
            agent_id="agent-123",
            energy_balance=energy_manager.get_balance(),
            penalty_config=penalty_config
        )
    ]
}

# 在 Agent 发现端点返回此 AgentCard
# GET /.well-known/agent
```

#### 5. 在 A2A 消息中包含 A2E 扩展头

```python
import requests

# 发送 A2A 请求时包含 A2E 扩展头
headers = {
    "Content-Type": "application/a2a+json",
    "A2A-Extensions": A2E_EXTENSION_URI  # 声明使用 A2E 扩展
}

# 任务请求包含能量定价元数据
task_request = {
    "message": {
        "role": "user",
        "parts": [{"text": "执行数据分析任务"}]
    },
    "metadata": {
        A2E_EXTENSION_URI: {
            "type": "EnergyPricingMetadata",
            "estimated_cost_kwh": 10.0,
            "offered_reward_kwh": 15.0,
            "agent_bid_price_kwh": 12.0,
            "actual_consumption_kwh": 0.0
        }
    }
}

response = requests.post(
    "https://agent.example.com/a2a/message",
    json=task_request,
    headers=headers
)
```

---

## 数据结构说明

### EnergyAccount (能量账户)

```python
{
    A2E_EXTENSION_URI: {
        "type": "EnergyAccount",
        "agent_id": "agent-123",
        "energy_balance_kwh": 100.0,
        "energy_credit_limit_kwh": 50.0,
        "last_settlement_timestamp_ms": 1704067200000
    }
}
```

- `energy_balance_kwh`: 当前能量余额 (千瓦时当量)
- `energy_credit_limit_kwh`: 信用透支额度
- `last_settlement_timestamp_ms`: 最后结算时间戳

### EnergyPricingMetadata (定价元数据)

```python
{
    A2E_EXTENSION_URI: {
        "type": "EnergyPricingMetadata",
        "estimated_cost_kwh": 10.0,
        "offered_reward_kwh": 15.0,
        "agent_bid_price_kwh": 12.0,
        "actual_consumption_kwh": 8.5
    }
}
```

- `estimated_cost_kwh`: 预估执行能耗
- `offered_reward_kwh`: 任务完成奖励
- `agent_bid_price_kwh`: 智能体竞价 (拍卖机制)
- `actual_consumption_kwh`: 实际结算消耗

### PenaltyConfig (惩罚配置)

```python
{
    A2E_EXTENSION_URI: {
        "type": "PenaltyConfig",
        "severity": "hard",  # 或 "soft"
        "energy_depletion_threshold": 5.0,
        "suspension_duration_seconds": 3600
    }
}
```

- `severity`: 惩罚严重程度 ("soft" 或 "hard")
  - `soft`: 仅降低任务调度优先级
  - `hard`: 进程挂起 (模拟休眠/死亡)
- `energy_depletion_threshold`: 触发惩罚的阈值
- `suspension_duration_seconds`: 挂起持续时间

---

## 核心决策逻辑

### 任务接受条件

智能体仅在满足以下条件时接受任务：

1. **生存检查**: 当前能量余额 ≥ 预估任务成本
2. **经济检查**: 任务奖励 ≥ 预估成本 × 风险因子 (默认 1.1)
3. **扩展支持**: 客户端声明支持 A2E 扩展

### 拒绝原因

| 错误码 | 原因 | 说明 |
|---------|------|------|
| `A2E_MISSING_PRICING` | 缺少定价元数据 | 任务必须包含 EnergyPricingMetadata |
| `A2E_INSUFFICIENT_ENERGY` | 能量不足 | 当前余额无法覆盖任务成本 |
| `A2E_LOW_ROI` | ROI 过低 | 奖励不足以覆盖成本和风险 |

---

## 与原始设计的改进

### 原始代码的问题

```python
# 原始实现 (不符合 A2A 规范)
pricing = task.metadata.get("a2a-ext-energy")  # 错误的键名
```

**问题：**
1. ❌ 未使用正确的扩展 URI 作为键
2. ❌ 缺少 A2A-Extensions 头处理
3. ❌ 元数据结构不符合 A2A 规范
4. ❌ 没有类型标识符

### 改进后的实现

```python
# 新实现 (完全符合 A2A 规范)
task_metadata = task.get("metadata", {})
pricing = EnergyPricingMetadata.from_task_metadata(task_metadata)

# 检查 A2A-Extensions 头
if not supports_a2e(a2a_headers):
    return TaskDecisionResult(...)
```

**改进：**
1. ✅ 使用标准扩展 URI: `https://a2a-protocol.org/extensions/energy-economy/v1`
2. ✅ 正确解析 `A2A-Extensions` HTTP 头
3. ✅ 元数据包含类型标识符和结构化字段
4. ✅ 与 A2A AgentCard 能力声明集成

---

## 扩展版本化

A2E 扩展遵循 A2A 版本化规范：

- **URI 格式**: `https://a2a-protocol.org/extensions/energy-economy/v1`
- **破坏性变更**: 必须创建新 URI (例如 `/v2`)
- **向后兼容**: v1 继续支持非破坏性变更

### 版本协商示例

```python
# 客户端声明支持的版本
headers = {
    "A2A-Extensions": "https://a2a-protocol.org/extensions/energy-economy/v1"
}

# 服务端检测兼容性
if A2E_EXTENSION_URI in parse_extensions_header(headers.get("A2A-Extensions", "")):
    # 支持 v1 版本
    pass
else:
    # 不支持 A2E 或版本不兼容
    pass
```

---

## 协议绑定支持

A2E 扩展支持所有 A2A 协议绑定：

### JSON-RPC Binding

```python
# 请求
{
    "jsonrpc": "2.0",
    "method": "a2a.sendMessage",
    "params": {
        "message": {...},
        "metadata": {
            A2E_EXTENSION_URI: {...}
        }
    },
    "id": 1
}
```

### HTTP+JSON/REST Binding

```http
POST /a2a/message HTTP/1.1
Host: agent.example.com
Content-Type: application/a2a+json
A2A-Extensions: https://a2a-protocol.org/extensions/energy-economy/v1

{
    "message": {...},
    "metadata": {
        "https://a2a-protocol.org/extensions/energy-economy/v1": {
            "type": "EnergyPricingMetadata",
            ...
        }
    }
}
```

### gRPC Binding

```protobuf
// 使用 A2A gRPC 定义并添加扩展元数据
message SendMessageRequest {
    Message message = 1;
    SendMessageConfiguration configuration = 2;
    google.protobuf.Struct metadata = 3;  // A2E 扩展数据
}
```

---

## 测试

运行包含的示例：

```bash
python a2e_protocol_extension.py
```

输出示例：

```
Task decision: accepted
Reason: Task accepted with energy reservation
Balance: 90.00 kWh

=== Agent Card A2E Extension ===
{
  "extension": {
    "uri": "https://a2a-protocol.org/extensions/energy-economy/v1",
    "version": "v1",
    ...
  },
  ...
}

=== Task Settlement ===
{
  "settlement_completed": true,
  "energy_consumed_kwh": 8.5,
  "energy_refunded_kwh": 1.5,
  "energy_rewarded_kwh": 15.0,
  "final_balance_kwh": 103.50
}
Final balance: 103.50 kWh
```

---

## A2A 规范引用

本实现严格遵循以下 A2A 协议规范章节：

- **Section 4.6 Extensions**: 扩展机制
- **Section 4.6.1 Extension Declaration**: 扩展声明
- **Section 4.4.1 AgentCard**: AgentCard 结构
- **Section 4.4.3 AgentCapabilities**: 能力声明
- **Section 3.2.5 Metadata**: 元数据结构
- **Section 14.2.2 A2A-Extensions Header**: HTTP 头机制

完整的 A2A 协议规范请参考:
https://a2a-protocol.org/latest/specification/

---

## 许可证

本实现基于 A2A 协议规范，用于学术研究和工程实践。

---

## 贡献

欢迎提出改进建议和错误报告。

---

## 作者

中国信息通信研究院
刘高峰, 潘彤, 余文艳 (通信作者)

**扩展 URI**: `https://a2a-protocol.org/extensions/energy-economy/v1`
**版本**: 1.0
**日期**: 2026年1月29日
