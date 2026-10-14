"""
Unit tests for Response Policy, Approval Gate, and Simulation Verification
"""
import pytest
from backend.policy import policy_engine, simulated_env
from backend.models import (
    ResponseActionType,
    PolicyDecision,
    ActionStatus
)


@pytest.fixture(autouse=True)
def reset_simulated_fleet():
    simulated_env.reset()


def test_consequential_action_requires_approval():
    """
    Host isolation on production systems must enforce human-in-the-loop approval.
    """
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_ISOLATE_HOST,
        target_entity="host-jump-prod-01",
        target_type="host",
        justification="Active C2 beaconing observed"
    )

    assert record.policy_decision == PolicyDecision.REQUIRE_APPROVAL
    assert record.status == ActionStatus.WAITING_FOR_APPROVAL


def test_unapproved_action_execution_is_blocked():
    """
    Attempting to execute an action before approval must raise PermissionError.
    """
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_ISOLATE_HOST,
        target_entity="host-jump-prod-01",
        target_type="host",
        justification="Active C2 beaconing observed"
    )

    with pytest.raises(PermissionError) as exc_info:
        policy_engine.execute_simulation(record.id)
    assert "Policy Gate Enforced" in str(exc_info.value)


def test_approved_action_lifecycle_and_verification():
    """
    Full approved lifecycle: PROPOSED -> WAITING_FOR_APPROVAL -> APPROVED -> EXECUTING -> VERIFIED.
    Verification must verify actual state change on simulated host.
    """
    # 1. Propose
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_ISOLATE_HOST,
        target_entity="host-jump-prod-01",
        target_type="host",
        justification="Isolate infected jump box"
    )
    assert simulated_env.hosts["host-jump-prod-01"]["network_state"] == "connected"

    # 2. Approve
    approved = policy_engine.approve_action(record.id, approver="Lead SecOps Analyst")
    assert approved.status == ActionStatus.APPROVED
    assert approved.approved_at is not None

    # 3. Execute & Verify
    verified = policy_engine.execute_simulation(record.id)
    assert verified.status == ActionStatus.VERIFIED
    assert "placed in isolated VLAN" in verified.verification_details

    # Verify actual state mutation in simulated environment
    assert simulated_env.hosts["host-jump-prod-01"]["network_state"] == "isolated"
    assert simulated_env.hosts["host-jump-prod-01"]["isolated"] is True


def test_denied_action_cannot_execute():
    """
    Denied actions transition to DENIED and cannot be executed.
    """
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_DISABLE_ACCOUNT,
        target_entity="id-jdoe",
        target_type="identity",
        justification="Prevent lateral credential abuse"
    )
    denied = policy_engine.deny_action(record.id, reason="User is currently on-call; investigate first")
    assert denied.status == ActionStatus.DENIED

    with pytest.raises(PermissionError):
        policy_engine.execute_simulation(record.id)


def test_automated_allow_action():
    """
    Non-destructive simulated actions (e.g. perimeter block) are pre-approved under policy.
    """
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_BLOCK_INDICATOR,
        target_entity="ind-c2-ip",
        target_type="indicator",
        justification="Block confirmed C2 external IP"
    )
    assert record.policy_decision == PolicyDecision.ALLOW
    assert record.status == ActionStatus.APPROVED

    verified = policy_engine.execute_simulation(record.id)
    assert verified.status == ActionStatus.VERIFIED
    assert simulated_env.indicators["ind-c2-ip"]["perimeter_blocked"] is True


def test_failed_verification_for_missing_entity():
    """
    If simulated action targets an unknown entity, it transitions to FAILED.
    """
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_ISOLATE_HOST,
        target_entity="non-existent-host",
        target_type="host",
        justification="Test failure handling"
    )
    policy_engine.approve_action(record.id)
    failed = policy_engine.execute_simulation(record.id)
    assert failed.status == ActionStatus.FAILED
    assert "not found" in failed.verification_details
