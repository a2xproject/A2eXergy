"""
Test Suite for A2E Protocol Extension
"""

import pytest
from a2e_protocol_extension import (
    EnergyAccountManager,
    EnergyAccount,
    EnergyPricingMetadata,
    PenaltyConfig,
    PenaltySeverity,
    A2EAgentMiddleware,
    TaskDecision,
    A2E_EXTENSION_URI,
    A2A_EXTENSIONS_HEADER,
    supports_a2e,
    get_a2e_extensions_header
)


class TestEnergyAccountManager:
    """Test cases for EnergyAccountManager"""

    def setup_method(self):
        """Setup test fixtures"""
        self.energy_manager = EnergyAccountManager(
            agent_id="test-agent",
            initial_balance_kwh=100.0,
            credit_limit_kwh=50.0
        )

    def test_initial_balance(self):
        """Test initial balance is set correctly"""
        assert self.energy_manager.get_balance() == 100.0

    def test_available_balance_includes_credit(self):
        """Test available balance includes credit limit"""
        assert self.energy_manager.get_available_balance() == 150.0

    def test_deduct_sufficient_funds(self):
        """Test deducting when sufficient funds"""
        result = self.energy_manager.deduct(50.0, "task_execution")
        assert result is True
        assert self.energy_manager.get_balance() == 50.0

    def test_deduct_insufficient_funds(self):
        """Test deducting when insufficient funds"""
        result = self.energy_manager.deduct(200.0, "task_execution")
        assert result is False
        assert self.energy_manager.get_balance() == 100.0

    def test_add_energy(self):
        """Test adding energy to account"""
        self.energy_manager.add(25.0, "task_reward")
        assert self.energy_manager.get_balance() == 125.0

    def test_transaction_history(self):
        """Test transaction history recording"""
        self.energy_manager.deduct(10.0, "task_execution")
        self.energy_manager.add(15.0, "task_reward")

        assert len(self.energy_manager.transaction_history) == 2
        assert self.energy_manager.transaction_history[0]["type"] == "debit"
        assert self.energy_manager.transaction_history[1]["type"] == "credit"


class TestEnergyAccount:
    """Test cases for EnergyAccount dataclass"""

    def test_to_metadata_dict(self):
        """Test converting to A2A metadata format"""
        account = EnergyAccount(
            agent_id="test-agent",
            energy_balance_kwh=100.0,
            energy_credit_limit_kwh=50.0,
            last_settlement_timestamp_ms=1234567890000
        )

        metadata = account.to_metadata_dict()

        assert A2E_EXTENSION_URI in metadata
        assert metadata[A2E_EXTENSION_URI]["type"] == "EnergyAccount"
        assert metadata[A2E_EXTENSION_URI]["agent_id"] == "test-agent"
        assert metadata[A2E_EXTENSION_URI]["energy_balance_kwh"] == 100.0

    def test_from_metadata_dict(self):
        """Test creating from A2A metadata format"""
        metadata = {
            A2E_EXTENSION_URI: {
                "type": "EnergyAccount",
                "agent_id": "test-agent",
                "energy_balance_kwh": 100.0,
                "energy_credit_limit_kwh": 50.0,
                "last_settlement_timestamp_ms": 1234567890000
            }
        }

        account = EnergyAccount.from_metadata_dict(metadata)

        assert account is not None
        assert account.agent_id == "test-agent"
        assert account.energy_balance_kwh == 100.0

    def test_from_metadata_dict_missing_extension(self):
        """Test creating from metadata without A2E extension"""
        metadata = {"other_key": {}}
        account = EnergyAccount.from_metadata_dict(metadata)
        assert account is None


class TestEnergyPricingMetadata:
    """Test cases for EnergyPricingMetadata dataclass"""

    def test_to_metadata_dict(self):
        """Test converting to A2A metadata format"""
        pricing = EnergyPricingMetadata(
            estimated_cost_kwh=10.0,
            offered_reward_kwh=15.0,
            agent_bid_price_kwh=12.0,
            actual_consumption_kwh=8.5
        )

        metadata = pricing.to_metadata_dict()

        assert A2E_EXTENSION_URI in metadata
        assert metadata[A2E_EXTENSION_URI]["type"] == "EnergyPricingMetadata"
        assert metadata[A2E_EXTENSION_URI]["estimated_cost_kwh"] == 10.0
        assert metadata[A2E_EXTENSION_URI]["offered_reward_kwh"] == 15.0

    def test_from_task_metadata(self):
        """Test extracting from task metadata"""
        task_metadata = {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": 10.0,
                "offered_reward_kwh": 15.0,
                "agent_bid_price_kwh": 12.0,
                "actual_consumption_kwh": 8.5
            }
        }

        pricing = EnergyPricingMetadata.from_task_metadata(task_metadata)

        assert pricing is not None
        assert pricing.estimated_cost_kwh == 10.0
        assert pricing.offered_reward_kwh == 15.0

    def test_from_task_metadata_missing(self):
        """Test extracting from metadata without A2E"""
        task_metadata = {"other_key": {}}
        pricing = EnergyPricingMetadata.from_task_metadata(task_metadata)
        assert pricing is None


class TestPenaltyConfig:
    """Test cases for PenaltyConfig dataclass"""

    def test_to_metadata_dict(self):
        """Test converting to A2A metadata format"""
        config = PenaltyConfig(
            severity=PenaltySeverity.HARD,
            energy_depletion_threshold=5.0,
            suspension_duration_seconds=3600
        )

        metadata = config.to_metadata_dict()

        assert A2E_EXTENSION_URI in metadata
        assert metadata[A2E_EXTENSION_URI]["type"] == "PenaltyConfig"
        assert metadata[A2E_EXTENSION_URI]["severity"] == "hard"
        assert metadata[A2E_EXTENSION_URI]["suspension_duration_seconds"] == 3600


class TestA2EAgentMiddleware:
    """Test cases for A2EAgentMiddleware"""

    def setup_method(self):
        """Setup test fixtures"""
        self.energy_manager = EnergyAccountManager(
            agent_id="test-agent",
            initial_balance_kwh=100.0,
            credit_limit_kwh=50.0
        )

        self.penalty_config = PenaltyConfig(
            severity=PenaltySeverity.HARD,
            energy_depletion_threshold=5.0,
            suspension_duration_seconds=3600
        )

        self.middleware = A2EAgentMiddleware(
            agent_id="test-agent",
            energy_manager=self.energy_manager,
            penalty_config=self.penalty_config,
            risk_factor=1.1
        )

    def test_accept_task_with_sufficient_energy(self):
        """Test accepting a task with sufficient energy and good ROI"""
        task = {
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

        headers = {A2A_EXTENSIONS_HEADER: A2E_EXTENSION_URI}
        result = self.middleware.handle_a2a_task(task, headers)

        assert result.decision == TaskDecision.ACCEPTED
        assert self.energy_manager.get_balance() == 90.0  # Pre-deducted

    def test_reject_task_insufficient_energy(self):
        """Test rejecting a task due to insufficient energy"""
        task = {
            "id": "task-002",
            "metadata": {
                A2E_EXTENSION_URI: {
                    "type": "EnergyPricingMetadata",
                    "estimated_cost_kwh": 200.0,  # More than available
                    "offered_reward_kwh": 250.0,
                    "agent_bid_price_kwh": 220.0,
                    "actual_consumption_kwh": 0.0
                }
            }
        }

        headers = {A2A_EXTENSIONS_HEADER: A2E_EXTENSION_URI}
        result = self.middleware.handle_a2a_task(task, headers)

        assert result.decision == TaskDecision.REJECTED
        assert result.metadata.get("error_code") == "A2E_INSUFFICIENT_ENERGY"

    def test_reject_task_low_roi(self):
        """Test rejecting a task due to low ROI"""
        task = {
            "id": "task-003",
            "metadata": {
                A2E_EXTENSION_URI: {
                    "type": "EnergyPricingMetadata",
                    "estimated_cost_kwh": 10.0,
                    "offered_reward_kwh": 10.0,  # Low reward
                    "agent_bid_price_kwh": 11.0,
                    "actual_consumption_kwh": 0.0
                }
            }
        }

        headers = {A2A_EXTENSIONS_HEADER: A2E_EXTENSION_URI}
        result = self.middleware.handle_a2a_task(task, headers)

        assert result.decision == TaskDecision.REJECTED
        assert result.metadata.get("error_code") == "A2E_LOW_ROI"

    def test_reject_task_missing_pricing(self):
        """Test rejecting a task without pricing metadata"""
        task = {
            "id": "task-004",
            "metadata": {}
        }

        headers = {A2A_EXTENSIONS_HEADER: A2E_EXTENSION_URI}
        result = self.middleware.handle_a2a_task(task, headers)

        assert result.decision == TaskDecision.REJECTED
        assert result.metadata.get("error_code") == "A2E_MISSING_PRICING"

    def test_accept_task_without_a2e_header(self):
        """Test accepting a task without A2E header (basic mode)"""
        task = {
            "id": "task-005",
            "metadata": {}
        }

        headers = {"Content-Type": "application/a2a+json"}  # No A2E header
        result = self.middleware.handle_a2a_task(task, headers)

        assert result.decision == TaskDecision.ACCEPTED

    def test_settle_task_completion(self):
        """Test settling a completed task"""
        # First accept a task
        task = {
            "id": "task-006",
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

        headers = {A2A_EXTENSIONS_HEADER: A2E_EXTENSION_URI}
        self.middleware.handle_a2a_task(task, headers)

        # Then settle it
        settlement = self.middleware.settle_task_completion(
            task_metadata=task["metadata"],
            actual_consumption_kwh=8.5
        )

        assert settlement["settlement_completed"] is True
        assert settlement["energy_consumed_kwh"] == 8.5
        assert settlement["energy_refunded_kwh"] == 1.5
        assert settlement["energy_rewarded_kwh"] == 15.0
        # Balance: 100 - 10 (pre-deduct) + 1.5 (refund) + 15 (reward) = 106.5
        assert self.energy_manager.get_balance() == 106.5


class TestHelperFunctions:
    """Test cases for helper functions"""

    def test_get_a2e_extensions_header(self):
        """Test generating A2A-Extensions header"""
        header = get_a2e_extensions_header()
        assert header == A2E_EXTENSION_URI

    def test_supports_a2e_with_header(self):
        """Test checking A2E support with header present"""
        headers = {A2A_EXTENSIONS_HEADER: A2E_EXTENSION_URI}
        assert supports_a2e(headers) is True

    def test_supports_a2e_without_header(self):
        """Test checking A2E support without header"""
        headers = {"Content-Type": "application/a2a+json"}
        assert supports_a2e(headers) is False

    def test_supports_a2e_with_multiple_extensions(self):
        """Test checking A2E support with multiple extensions"""
        headers = {
            A2A_EXTENSIONS_HEADER: "extension1, " + A2E_EXTENSION_URI + ", extension2"
        }
        assert supports_a2e(headers) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
