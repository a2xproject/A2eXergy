#!/usr/bin/env python3
"""
A2Exergy Basic Usage Examples

Demonstrates how to use the A2E protocol extension for energy-based agent economy.
"""

from a2e_protocol_extension import (
    EnergyAccountManager,
    PenaltyConfig,
    PenaltySeverity,
    A2EAgentMiddleware,
    A2E_EXTENSION_URI,
    TaskDecision
)


def example_basic_initialization():
    """Example 1: Basic initialization of energy components"""
    print("=" * 60)
    print("Example 1: Basic Initialization")
    print("=" * 60)

    # Create energy account manager
    energy_manager = EnergyAccountManager(
        agent_id="agent-001",
        initial_balance_kwh=100.0,
        credit_limit_kwh=50.0
    )

    # Configure penalty strategy
    penalty_config = PenaltyConfig(
        severity=PenaltySeverity.HARD,
        energy_depletion_threshold=5.0,
        suspension_duration_seconds=3600
    )

    # Initialize middleware
    middleware = A2EAgentMiddleware(
        agent_id="agent-001",
        energy_manager=energy_manager,
        penalty_config=penalty_config,
        risk_factor=1.1
    )

    print(f"✓ Initial balance: {energy_manager.get_balance():.2f} kWh")
    print(f"✓ Available balance (with credit): {energy_manager.get_available_balance():.2f} kWh")
    print()


def example_task_handling():
    """Example 2: Handling an A2A task with energy economy"""
    print("=" * 60)
    print("Example 2: Task Handling")
    print("=" * 60)

    # Setup
    energy_manager = EnergyAccountManager(
        agent_id="agent-001",
        initial_balance_kwh=100.0,
        credit_limit_kwh=50.0
    )

    penalty_config = PenaltyConfig(
        severity=PenaltySeverity.HARD,
        energy_depletion_threshold=5.0,
        suspension_duration_seconds=3600
    )

    middleware = A2EAgentMiddleware(
        agent_id="agent-001",
        energy_manager=energy_manager,
        penalty_config=penalty_config,
        risk_factor=1.1
    )

    # Create a task request with A2E metadata
    task_request = {
        "id": "task-001",
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

    # HTTP headers with A2E extension declaration
    http_headers = {
        "Content-Type": "application/a2a+json",
        "A2A-Extensions": A2E_EXTENSION_URI
    }

    # Handle the task
    result = middleware.handle_a2a_task(task_request, http_headers)

    print(f"Task ID: {task_request['id']}")
    print(f"Decision: {result.decision}")
    print(f"Reason: {result.reason}")
    print(f"Current balance: {energy_manager.get_balance():.2f} kWh")
    print()


def example_task_settlement():
    """Example 3: Settling a completed task"""
    print("=" * 60)
    print("Example 3: Task Settlement")
    print("=" * 60)

    # Setup
    energy_manager = EnergyAccountManager(
        agent_id="agent-001",
        initial_balance_kwh=100.0,
        credit_limit_kwh=50.0
    )

    penalty_config = PenaltyConfig(
        severity=PenaltySeverity.HARD,
        energy_depletion_threshold=5.0,
        suspension_duration_seconds=3600
    )

    middleware = A2EAgentMiddleware(
        agent_id="agent-001",
        energy_manager=energy_manager,
        penalty_config=penalty_config,
        risk_factor=1.1
    )

    # Simulate task execution
    task_metadata = {
        A2E_EXTENSION_URI: {
            "type": "EnergyPricingMetadata",
            "estimated_cost_kwh": 10.0,
            "offered_reward_kwh": 15.0,
            "agent_bid_price_kwh": 12.0,
            "actual_consumption_kwh": 0.0
        }
    }

    # Settle the task (actual consumption was 8.5 kWh)
    settlement = middleware.settle_task_completion(
        task_metadata=task_metadata,
        actual_consumption_kwh=8.5
    )

    print("Settlement Results:")
    for key, value in settlement.items():
        print(f"  {key}: {value}")

    print(f"\nFinal balance: {energy_manager.get_balance():.2f} kWh")
    print()


def example_rejected_task():
    """Example 4: Handling a rejected task (insufficient energy)"""
    print("=" * 60)
    print("Example 4: Rejected Task (Low Balance)")
    print("=" * 60)

    # Setup with low initial balance
    energy_manager = EnergyAccountManager(
        agent_id="agent-001",
        initial_balance_kwh=5.0,  # Very low balance
        credit_limit_kwh=10.0
    )

    penalty_config = PenaltyConfig(
        severity=PenaltySeverity.HARD,
        energy_depletion_threshold=5.0,
        suspension_duration_seconds=3600
    )

    middleware = A2EAgentMiddleware(
        agent_id="agent-001",
        energy_manager=energy_manager,
        penalty_config=penalty_config,
        risk_factor=1.1
    )

    # Task requiring more energy than available
    task_request = {
        "id": "task-002",
        "metadata": {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": 20.0,  # Requires more than available
                "offered_reward_kwh": 25.0,
                "agent_bid_price_kwh": 22.0,
                "actual_consumption_kwh": 0.0
            }
        }
    }

    http_headers = {
        "Content-Type": "application/a2a+json",
        "A2A-Extensions": A2E_EXTENSION_URI
    }

    result = middleware.handle_a2a_task(task_request, http_headers)

    print(f"Decision: {result.decision}")
    print(f"Reason: {result.reason}")
    if result.metadata:
        print(f"Error code: {result.metadata.get('error_code')}")
    print()


def example_agent_card():
    """Example 5: Generating AgentCard with A2E extension"""
    print("=" * 60)
    print("Example 5: AgentCard Extension")
    print("=" * 60)

    from a2e_protocol_extension import get_a2e_agent_card_extension
    import json

    energy_manager = EnergyAccountManager(
        agent_id="agent-001",
        initial_balance_kwh=100.0,
        credit_limit_kwh=50.0
    )

    penalty_config = PenaltyConfig(
        severity=PenaltySeverity.HARD,
        energy_depletion_threshold=5.0,
        suspension_duration_seconds=3600
    )

    # Generate AgentCard extension
    agent_card_extension = get_a2e_agent_card_extension(
        agent_id="agent-001",
        energy_balance=energy_manager.get_balance(),
        penalty_config=penalty_config
    )

    print("AgentCard A2E Extension:")
    print(json.dumps(agent_card_extension, indent=2))
    print()


def example_full_workflow():
    """Example 6: Complete workflow from task to settlement"""
    print("=" * 60)
    print("Example 6: Complete Workflow")
    print("=" * 60)

    # Initialize
    energy_manager = EnergyAccountManager(
        agent_id="agent-001",
        initial_balance_kwh=100.0,
        credit_limit_kwh=50.0
    )

    penalty_config = PenaltyConfig(
        severity=PenaltySeverity.HARD,
        energy_depletion_threshold=5.0,
        suspension_duration_seconds=3600
    )

    middleware = A2EAgentMiddleware(
        agent_id="agent-001",
        energy_manager=energy_manager,
        penalty_config=penalty_config,
        risk_factor=1.1
    )

    print(f"Initial balance: {energy_manager.get_balance():.2f} kWh")

    # Simulate 3 tasks
    tasks = [
        {"estimated": 10.0, "reward": 15.0, "actual": 8.5},
        {"estimated": 5.0, "reward": 6.0, "actual": 4.2},
        {"estimated": 15.0, "reward": 20.0, "actual": 14.0},
    ]

    for i, task_info in enumerate(tasks, 1):
        print(f"\n--- Task {i} ---")

        task = {
            "id": f"task-{i}",
            "metadata": {
                A2E_EXTENSION_URI: {
                    "type": "EnergyPricingMetadata",
                    "estimated_cost_kwh": task_info["estimated"],
                    "offered_reward_kwh": task_info["reward"],
                    "agent_bid_price_kwh": task_info["estimated"] * 1.1,
                    "actual_consumption_kwh": 0.0
                }
            }
        }

        http_headers = {
            "Content-Type": "application/a2a+json",
            "A2A-Extensions": A2E_EXTENSION_URI
        }

        # Handle task
        result = middleware.handle_a2a_task(task, http_headers)
        print(f"Task {i} decision: {result.decision}")

        if result.decision == TaskDecision.ACCEPTED:
            # Simulate execution and settlement
            settlement = middleware.settle_task_completion(
                task_metadata=task["metadata"],
                actual_consumption_kwh=task_info["actual"]
            )
            print(f"  Consumed: {task_info['actual']:.2f} kWh")
            print(f"  Earned: {task_info['reward']:.2f} kWh")

        print(f"  Current balance: {energy_manager.get_balance():.2f} kWh")

    print(f"\nFinal balance: {energy_manager.get_balance():.2f} kWh")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print(" A2Exergy - Basic Usage Examples")
    print("=" * 60 + "\n")

    example_basic_initialization()
    example_task_handling()
    example_task_settlement()
    example_rejected_task()
    example_agent_card()
    example_full_workflow()

    print("=" * 60)
    print(" All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
