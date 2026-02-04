"""
A2E (Agent-to-Energy) Protocol Extension
======================================
A2A Protocol Extension for Energy-Based Economy System

Extension URI: https://a2a-protocol.org/extensions/energy-economy/v1

This module provides a compliant A2A extension that enables agents to participate
in an energy-based economy where physical energy consumption serves as the value anchor.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import time
from abc import ABC, abstractmethod


# ============================================================================
# A2A Extension Declaration - Section 4.6.1
# ============================================================================

A2E_EXTENSION_URI = "https://a2a-protocol.org/extensions/energy-economy/v1"
A2A_EXTENSIONS_HEADER = "A2A-Extensions"


def get_a2e_extensions_header() -> str:
    """
    Returns the A2A-Extensions header value for A2E support.
    
    Per A2A Spec Section 14.2.2:
    The A2A-Extensions header contains a comma-separated list of 
    extension URIs that the client wants to use for the request.
    """
    return A2E_EXTENSION_URI


def parse_extensions_header(header_value: str) -> List[str]:
    """
    Parses A2A-Extensions header into a list of extension URIs.
    
    Args:
        header_value: Comma-separated list of extension URIs
        
    Returns:
        List of extension URIs
    """
    if not header_value:
        return []
    return [uri.strip() for uri in header_value.split(",") if uri.strip()]


def supports_a2e(headers: Dict[str, str]) -> bool:
    """
    Checks if A2E extension is supported based on A2A-Extensions header.
    
    Args:
        headers: HTTP headers dictionary
        
    Returns:
        True if A2E extension is present
    """
    extensions_header = headers.get(A2A_EXTENSIONS_HEADER, "")
    extensions = parse_extensions_header(extensions_header)
    return A2E_EXTENSION_URI in extensions


# ============================================================================
# A2A Extension Metadata Structure - Section 3.2.5 (Metadata)
# ============================================================================

@dataclass
class EnergyAccount:
    """
    Agent Energy Account Status
    
    Represents the agent's energy wallet containing balance, credit, and settlement info.
    This is stored as extension metadata in A2A AgentCard and Messages.
    
    Per A2A Spec: Extensions contribute metadata to Messages and Artifacts.
    """
    agent_id: str                          # Corresponds to AgentCard.agentId
    energy_balance_kwh: float               # Current energy balance in kWh-equivalent
    energy_credit_limit_kwh: float         # Credit overdraft limit in kWh-equivalent
    last_settlement_timestamp_ms: int        # Unix timestamp of last settlement
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        """Convert to A2A metadata dictionary structure."""
        return {
            A2E_EXTENSION_URI: {
                "type": "EnergyAccount",
                "agent_id": self.agent_id,
                "energy_balance_kwh": self.energy_balance_kwh,
                "energy_credit_limit_kwh": self.energy_credit_limit_kwh,
                "last_settlement_timestamp_ms": self.last_settlement_timestamp_ms
            }
        }
    
    @classmethod
    def from_metadata_dict(cls, metadata: Dict[str, Any]) -> Optional['EnergyAccount']:
        """
        Create EnergyAccount from A2A metadata dictionary.
        
        Args:
            metadata: A2A metadata dictionary containing extension data
            
        Returns:
            EnergyAccount instance or None if extension not present
        """
        if A2E_EXTENSION_URI not in metadata:
            return None
        
        ext_data = metadata[A2E_EXTENSION_URI]
        if ext_data.get("type") != "EnergyAccount":
            return None
            
        return cls(
            agent_id=ext_data["agent_id"],
            energy_balance_kwh=ext_data["energy_balance_kwh"],
            energy_credit_limit_kwh=ext_data["energy_credit_limit_kwh"],
            last_settlement_timestamp_ms=ext_data["last_settlement_timestamp_ms"]
        )


class PenaltySeverity(Enum):
    """
    Severity level for energy depletion penalties.
    
    Per A2A Spec Section 4.6.1: Extensions use structured types.
    """
    SOFT = "soft"    # Reduce task scheduling priority
    HARD = "hard"    # Suspend process (simulate sleep/death)


@dataclass
class PenaltyConfig:
    """
    Survival Penalty Strategy Configuration
    
    Defines system response when agent energy is depleted.
    Part of A2E extension configuration in AgentCard.capabilities.
    """
    severity: PenaltySeverity              # SOFT or HARD penalty type
    energy_depletion_threshold: float     # Threshold (kWh) to trigger penalty
    suspension_duration_seconds: int      # Duration for HARD penalty
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        """Convert to A2A metadata dictionary structure."""
        return {
            A2E_EXTENSION_URI: {
                "type": "PenaltyConfig",
                "severity": self.severity.value,
                "energy_depletion_threshold": self.energy_depletion_threshold,
                "suspension_duration_seconds": self.suspension_duration_seconds
            }
        }


@dataclass
class EnergyPricingMetadata:
    """
    Task Energy Pricing and Transaction Metadata
    
    Agents declare task cost, reward, and bidding information.
    Attached to A2A Task metadata to enable energy-based transactions.
    
    Per A2A Spec Section 3.2.5: Service parameters include metadata.
    """
    estimated_cost_kwh: float      # Estimated execution energy cost
    offered_reward_kwh: float      # Task completion reward
    agent_bid_price_kwh: float    # Agent bid price (for auction mechanism)
    actual_consumption_kwh: float  # Actual settled consumption
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        """Convert to A2A metadata dictionary structure."""
        return {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": self.estimated_cost_kwh,
                "offered_reward_kwh": self.offered_reward_kwh,
                "agent_bid_price_kwh": self.agent_bid_price_kwh,
                "actual_consumption_kwh": self.actual_consumption_kwh
            }
        }
    
    @classmethod
    def from_task_metadata(cls, task_metadata: Dict[str, Any]) -> Optional['EnergyPricingMetadata']:
        """
        Extract EnergyPricingMetadata from A2A Task metadata.
        
        Args:
            task_metadata: A2A Task metadata dictionary
            
        Returns:
            EnergyPricingMetadata instance or None if not present
        """
        if A2E_EXTENSION_URI not in task_metadata:
            return None
        
        ext_data = task_metadata[A2E_EXTENSION_URI]
        if ext_data.get("type") != "EnergyPricingMetadata":
            return None
            
        return cls(
            estimated_cost_kwh=ext_data["estimated_cost_kwh"],
            offered_reward_kwh=ext_data["offered_reward_kwh"],
            agent_bid_price_kwh=ext_data["agent_bid_price_kwh"],
            actual_consumption_kwh=ext_data["actual_consumption_kwh"]
        )


# ============================================================================
# A2A Extension Capability Declaration - Section 4.4.3 (AgentCapabilities)
# ============================================================================

@dataclass
class EnergyEconomyCapability:
    """
    A2A Extension Capability Declaration
    
    Per A2A Spec Section 4.6.1: "A declaration of a protocol extension 
    supported by an Agent."
    
    Used in AgentCard.capabilities to declare A2E support.
    """
    uri: str = A2E_EXTENSION_URI
    version: str = "v1"
    name: str = "energy-economy"
    description: str = "Energy-based economic system for agent interactions"
    supported_features: List[str] = field(default_factory=lambda: [
        "energy-account",
        "energy-pricing",
        "penalty-config",
        "energy-transfer"
    ])
    
    def to_capability_dict(self) -> Dict[str, Any]:
        """
        Convert to A2A AgentCapabilities format.
        
        Per A2A Spec Section 4.6.1:
        Extension includes uri identifier and version information.
        """
        return {
            "extension": {
                "uri": self.uri,
                "version": self.version,
                "name": self.name,
                "description": self.description,
                "supported_features": self.supported_features
            }
        }


# ============================================================================
# Energy Account Manager
# ============================================================================

class EnergyAccountManager:
    """
    Manages agent's energy account with transaction tracking.
    
    Implements survival mechanism: agents must earn energy to maintain operation.
    """
    
    def __init__(self, agent_id: str, initial_balance_kwh: float = 0.0, 
                 credit_limit_kwh: float = 0.0):
        self.agent_id = agent_id
        self.balance = initial_balance_kwh
        self.credit_limit = credit_limit_kwh
        self.last_settlement = int(time.time() * 1000)
        self.transaction_history: List[Dict[str, Any]] = []
    
    def get_balance(self) -> float:
        """Get current energy balance including credit."""
        return self.balance
    
    def get_available_balance(self) -> float:
        """Get available balance including credit limit."""
        return self.balance + self.credit_limit
    
    def deduct(self, amount_kwh: float, reason: str = "task_execution") -> bool:
        """
        Deduct energy from account.
        
        Args:
            amount_kwh: Amount to deduct in kWh
            reason: Reason for deduction
            
        Returns:
            True if successful, False if insufficient funds
        """
        if self.get_available_balance() < amount_kwh:
            return False
        
        self.balance -= amount_kwh
        self._record_transaction(amount_kwh, "debit", reason)
        return True
    
    def add(self, amount_kwh: float, reason: str = "task_reward") -> None:
        """
        Add energy to account.
        
        Args:
            amount_kwh: Amount to add in kWh
            reason: Reason for addition
        """
        self.balance += amount_kwh
        self._record_transaction(amount_kwh, "credit", reason)
    
    def _record_transaction(self, amount_kwh: float, tx_type: str, reason: str) -> None:
        """Record a transaction in history."""
        self.transaction_history.append({
            "amount_kwh": amount_kwh,
            "type": tx_type,
            "reason": reason,
            "balance_after": self.balance,
            "timestamp_ms": int(time.time() * 1000)
        })
    
    def get_account_metadata(self) -> Dict[str, Any]:
        """Get current account state as A2A metadata."""
        account = EnergyAccount(
            agent_id=self.agent_id,
            energy_balance_kwh=self.balance,
            energy_credit_limit_kwh=self.credit_limit,
            last_settlement_timestamp_ms=self.last_settlement
        )
        return account.to_metadata_dict()


# ============================================================================
# A2A-E2E Agent Middleware - Core Task Handling Logic
# ============================================================================

class TaskDecision:
    """Result of task acceptance decision."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class TaskDecisionResult:
    """Result of energy-aware task decision."""
    decision: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class A2EAgentMiddleware:
    """
    Middleware for A2A agents to participate in energy economy.
    
    Implements energy-aware decision logic:
    1. Parse A2E extension metadata from A2A Task
    2. Evaluate task ROI based on energy cost vs reward
    3. Make acceptance/rejection decision
    4. Manage energy account transactions
    
    Per A2A Spec: Extensions should integrate seamlessly with core operations.
    """
    
    def __init__(self, agent_id: str, energy_manager: EnergyAccountManager,
                 penalty_config: PenaltyConfig, risk_factor: float = 1.1):
        self.agent_id = agent_id
        self.energy_manager = energy_manager
        self.penalty_config = penalty_config
        self.risk_factor = risk_factor  # ROI safety margin
    
    def handle_a2a_task(self, task: Dict[str, Any], 
                        a2a_headers: Dict[str, str]) -> TaskDecisionResult:
        """
        Handle A2A task request with energy economy logic.
        
        Args:
            task: A2A Task object containing metadata
            a2a_headers: HTTP headers including A2A-Extensions
            
        Returns:
            TaskDecisionResult indicating acceptance or rejection
        """
        # Step 1: Check if client supports A2E extension
        if not supports_a2e(a2a_headers):
            # Policy decision: accept or reject non-A2E tasks
            # Here we accept with a warning
            return TaskDecisionResult(
                decision=TaskDecision.ACCEPTED,
                reason="A2E extension not requested, proceeding with basic execution"
            )
        
        # Step 2: Extract A2E metadata from task
        task_metadata = task.get("metadata", {})
        pricing = EnergyPricingMetadata.from_task_metadata(task_metadata)
        
        if pricing is None:
            # No economic incentive provided - reject based on policy
            return TaskDecisionResult(
                decision=TaskDecision.REJECTED,
                reason="No energy reward provided (A2E metadata missing)",
                metadata={
                    "error_code": "A2E_MISSING_PRICING",
                    "error_message": "Task must include EnergyPricingMetadata"
                }
            )
        
        # Step 3: Survival logic check - sufficient energy?
        current_balance = self.energy_manager.get_available_balance()
        if current_balance < pricing.estimated_cost_kwh:
            return TaskDecisionResult(
                decision=TaskDecision.REJECTED,
                reason=f"Insufficient energy reserves: {current_balance:.3f}kWh < {pricing.estimated_cost_kwh:.3f}kWh",
                metadata={
                    "error_code": "A2E_INSUFFICIENT_ENERGY",
                    "current_balance_kwh": current_balance,
                    "required_kwh": pricing.estimated_cost_kwh
                }
            )
        
        # Step 4: Economic logic check - profitable ROI?
        min_reward = pricing.estimated_cost_kwh * self.risk_factor
        if pricing.offered_reward_kwh < min_reward:
            return TaskDecisionResult(
                decision=TaskDecision.REJECTED,
                reason=f"ROI too low: reward {pricing.offered_reward_kwh:.3f}kWh < minimum {min_reward:.3f}kWh",
                metadata={
                    "error_code": "A2E_LOW_ROI",
                    "offered_reward_kwh": pricing.offered_reward_kwh,
                    "minimum_reward_kwh": min_reward
                }
            )
        
        # Step 5: Accept task - pre-deduct energy
        success = self.energy_manager.deduct(
            pricing.estimated_cost_kwh,
            reason="task_execution"
        )
        
        if not success:
            return TaskDecisionResult(
                decision=TaskDecision.REJECTED,
                reason="Energy deduction failed",
                metadata={"error_code": "A2E_TRANSACTION_FAILED"}
            )
        
        return TaskDecisionResult(
            decision=TaskDecision.ACCEPTED,
            reason="Task accepted with energy reservation",
            metadata={
                "energy_reserved_kwh": pricing.estimated_cost_kwh,
                "expected_reward_kwh": pricing.offered_reward_kwh
            }
        )
    
    def settle_task_completion(self, task_metadata: Dict[str, Any], 
                           actual_consumption_kwh: float) -> Dict[str, Any]:
        """
        Settle energy account after task completion.
        
        Args:
            task_metadata: Original task metadata
            actual_consumption_kwh: Actual energy consumed during execution
            
        Returns:
            Settlement metadata with energy transfer
        """
        pricing = EnergyPricingMetadata.from_task_metadata(task_metadata)
        
        if pricing is None:
            return {"error": "No pricing metadata for settlement"}
        
        # Refund unused energy (if actual < estimated)
        difference = pricing.estimated_cost_kwh - actual_consumption_kwh
        if difference > 0:
            self.energy_manager.add(difference, "task_refund")
        
        # Add reward
        self.energy_manager.add(pricing.offered_reward_kwh, "task_reward")
        
        # Update settlement timestamp
        self.energy_manager.last_settlement = int(time.time() * 1000)
        
        return {
            "settlement_completed": True,
            "energy_consumed_kwh": actual_consumption_kwh,
            "energy_refunded_kwh": max(0, difference),
            "energy_rewarded_kwh": pricing.offered_reward_kwh,
            "final_balance_kwh": self.energy_manager.get_balance(),
            "settlement_metadata": self.energy_manager.get_account_metadata()
        }


# ============================================================================
# A2A Agent Card Extension - Section 4.4.1 (AgentCard)
# ============================================================================

def get_a2e_agent_card_extension(agent_id: str, 
                                energy_balance: float,
                                penalty_config: PenaltyConfig) -> Dict[str, Any]:
    """
    Generate A2E extension data for AgentCard.
    
    Per A2A Spec Section 4.4.1: AgentCard includes capabilities field.
    
    Args:
        agent_id: Agent identifier
        energy_balance: Current energy balance
        penalty_config: Penalty configuration
        
    Returns:
        Dictionary suitable for inclusion in AgentCard
    """
    # Create energy economy capability
    capability = EnergyEconomyCapability()
    
    # Create account state
    account = EnergyAccount(
        agent_id=agent_id,
        energy_balance_kwh=energy_balance,
        energy_credit_limit_kwh=0.0,
        last_settlement_timestamp_ms=int(time.time() * 1000)
    )
    
    return {
        "extension": {
            "uri": A2E_EXTENSION_URI,
            "version": capability.version,
            "name": capability.name,
            "description": capability.description,
            "supported_features": capability.supported_features
        },
        "account_state": account.to_metadata_dict(),
        "penalty_config": penalty_config.to_metadata_dict()
    }


# ============================================================================
# Usage Example - Integration with A2A Python SDK
# ============================================================================

if __name__ == "__main__":
    """
    Example: Integrating A2E middleware with an A2A agent.
    
    This demonstrates how to use the A2E extension with A2A protocol.
    """
    
    # Setup energy account
    energy_manager = EnergyAccountManager(
        agent_id="agent-123",
        initial_balance_kwh=100.0,
        credit_limit_kwh=50.0
    )
    
    # Setup penalty configuration
    penalty_config = PenaltyConfig(
        severity=PenaltySeverity.HARD,
        energy_depletion_threshold=5.0,
        suspension_duration_seconds=3600
    )
    
    # Initialize A2E middleware
    middleware = A2EAgentMiddleware(
        agent_id="agent-123",
        energy_manager=energy_manager,
        penalty_config=penalty_config,
        risk_factor=1.1
    )
    
    # Example 1: Receive A2A task with A2E extension
    task_a2e = {
        "id": "task-456",
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
    
    a2a_headers = {
        "A2A-Extensions": A2E_EXTENSION_URI
    }
    
    result = middleware.handle_a2a_task(task_a2e, a2a_headers)
    print(f"Task decision: {result.decision}")
    print(f"Reason: {result.reason}")
    print(f"Balance: {energy_manager.get_balance():.2f} kWh")
    
    # Example 2: Get Agent Card with A2E extension
    agent_card_extension = get_a2e_agent_card_extension(
        agent_id="agent-123",
        energy_balance=energy_manager.get_balance(),
        penalty_config=penalty_config
    )
    
    print("\n=== Agent Card A2E Extension ===")
    print(json.dumps(agent_card_extension, indent=2))
    
    # Example 3: Settle completed task
    print("\n=== Task Settlement ===")
    settlement = middleware.settle_task_completion(
        task_metadata=task_a2e["metadata"],
        actual_consumption_kwh=8.5
    )
    print(json.dumps(settlement, indent=2))
    print(f"Final balance: {energy_manager.get_balance():.2f} kWh")
