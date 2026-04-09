# A2eXergy: Energy Economy Extension for A2A Protocol

A third-party extension protocol for Google's A2A (Agent-to-Agent) protocol that introduces energy-based economic model to multi-agent systems.

---

## Overview

A2eXergy (Agent-to-Exergy) is a protocol extension that implements an energy economy system for AI agents, built on top of Google's A2A protocol. It introduces energy accounts, dynamic pricing, and survival mechanisms to create a self-regulating agent economy.

### Key Features

- **A2A Native Compliance**: Fully compatible with A2A protocol Section 4.6 Extension mechanism
- **Energy Account System**: Digital "wallet" for each agent to track energy balance
- **ROI-based Filtering**: Automatic rejection of low-value tasks (configurable threshold)
- **Survival Mechanism**: Process suspension when energy is depleted
- **Backward Compatible**: Works with standard A2A agents without modification

---

## Architecture

### Extension URI

```
https://a2a-protocol.org/extensions/energy-economy/v1
```

### Core Data Structures

**1. EnergyAccount**
```json
{
  "type": "EnergyAccount",
  "agent_id": "agent-123",
  "energy_balance_kwh": 100.0,
  "energy_credit_limit_kwh": 50.0,
  "last_settlement_timestamp_ms": 1704067200000
}
```

**2. EnergyPricingMetadata**
```json
{
  "type": "EnergyPricingMetadata",
  "estimated_cost_kwh": 10.0,
  "offered_reward_kwh": 15.0,
  "agent_bid_price_kwh": 12.0,
  "actual_consumption_kwh": 8.5
}
```

**3. PenaltyConfig**
```json
{
  "type": "PenaltyConfig",
  "severity": "hard",
  "energy_depletion_threshold": 5.0,
  "suspension_duration_seconds": 3600
}
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/a2xproject/A2eXergy.git
cd A2eXergy

# Install dependencies (optional, only for tests)
pip install httpx pytest
```

---

## Quick Start

### 1. Initialize Energy Account

```python
from a2e_protocol_extension import (
    EnergyAccountManager,
    A2EAgentMiddleware,
    PenaltyConfig,
    PenaltySeverity
)

# Create energy account manager
energy_manager = EnergyAccountManager(
    agent_id="agent-001",
    initial_balance_kwh=100.0,
    credit_limit_kwh=50.0
)

# Configure penalty strategy
penalty_config = PenaltyConfig(
    severity=PenaltySeverity.HARD,
    energy_depletion_threshold=5.0
)

# Create middleware
middleware = A2EAgentMiddleware(
    agent_id="agent-001",
    energy_manager=energy_manager,
    penalty_config=penalty_config,
    risk_factor=1.1  # ROI threshold = 10%
)
```

### 2. Handle Task Requests

```python
def handle_task(task: dict, http_headers: dict):
    # Process task through middleware
    result = middleware.handle_a2a_task(task, http_headers)
    
    if result.decision == TaskDecision.ACCEPTED:
        # Execute task
        execute_task(task)
        
        # Settle energy
        settlement = middleware.settle_task_completion(
            task_metadata=task.get("metadata", {}),
            actual_consumption_kwh=8.5
        )
        return {"status": "completed", "settlement": settlement}
    else:
        return {"status": "rejected", "reason": result.reason}
```

### 3. Include in A2A Messages

```python
import requests

headers = {
    "Content-Type": "application/a2a+json",
    "A2A-Extensions": "https://a2a-protocol.org/extensions/energy-economy/v1"
}

task_request = {
    "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Execute data analysis"}]
    },
    "metadata": {
        "https://a2a-protocol.org/extensions/energy-economy/v1": {
            "type": "EnergyPricingMetadata",
            "estimated_cost_kwh": 10.0,
            "offered_reward_kwh": 15.0
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

## Running the Servers

### Standard A2A Server

```bash
python servers/standard_a2a_server.py
# Runs on http://localhost:8001
```

### A2X Extended Server

```bash
python servers/a2x_server.py
# Runs on http://localhost:8002
```

---

## Running Tests

### HTTP Comparison Test

```bash
# Baseline test (100 tasks)
python tests/test_comparison.py

# High load test (200 tasks)
python tests/test_comparison.py exp2

# ROI sensitivity test
python tests/test_comparison.py exp3
```

### Compatibility Test

```bash
python tests/test_compatibility.py
```

### Unit Tests

```bash
pytest tests/test_a2e_extension.py -v
```

---

## Experiment Results

| Metric | A2A (Standard) | A2X (Energy Economy) | Difference |
|--------|-----------------|---------------------|------------|
| Energy Consumption | 1000 kWh | 425 kWh | **-57.5%** |
| Efficiency Ratio | 1.275 | 1.765 | **+38.4%** |
| Tasks Filtered | 0 | 50 | 50% |
| Latency Overhead | - | - | <1% |

**Key Findings:**
- Energy savings: 57.5%
- Efficiency improvement: 38.4%
- Low-value task filtering: 50% (ROI < 10%)
- Full backward compatibility with A2A protocol

---

## Project Structure

```
A2eXergy/
├── a2e_protocol_extension.py   # Core protocol implementation
├── servers/
│   ├── a2x_server.py           # A2X server with energy economy
│   └── standard_a2a_server.py  # Standard A2A server
├── tests/
│   ├── test_comparison.py      # HTTP comparison tests
│   ├── test_compatibility.py   # Compatibility tests
│   └── test_a2e_extension.py   # Unit tests
├── examples/
│   └── basic_usage.py          # Usage examples
└── README.md
```

---

## API Reference

### Core Classes

- `EnergyAccountManager`: Manages agent energy balance
- `EnergyPricingMetadata`: Task pricing information
- `A2EAgentMiddleware`: Middleware for task decision making
- `PenaltyConfig`: Survival mechanism configuration

### Decision Logic

An agent accepts a task only if:

1. **Survival Check**: Current balance >= Estimated cost
2. **Economic Check**: ROI >= Risk factor (default 10%)
3. **Extension Support**: Client declares A2X support

### Rejection Reasons

| Error Code | Reason | Description |
|------------|---------|-------------|
| `A2E_MISSING_PRICING` | Missing metadata | Task must include EnergyPricingMetadata |
| `A2E_INSUFFICIENT_ENERGY` | Insufficient balance | Cannot cover task cost |
| `A2E_LOW_ROI` | Low ROI | Reward insufficient for risk |

---

## References

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [A2A Protocol GitHub](https://github.com/google/a2a-python)

---

## License

MIT License

---

## Authors

China Academy of Information and Communications Technology (CAICT)  
Liu Gaofeng, Pan Tong, Yu Wenyan (Corresponding Author)

---

## Repository

https://github.com/a2xproject/A2eXergy
