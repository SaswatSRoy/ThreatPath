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
    simulated_env.reset(clear_storage=True)


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


def test_scenario_c_escalate_incident_verification_not_containment():
    """
    Regression Test for Issue 2:
    Scenario C selects SIMULATE_ESCALATE_INCIDENT.
    Verification feedback must be action-specific:
    - Must verify incident escalation ticketing
    - Must NOT claim host isolation, network disconnection, or containment
    """
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_ESCALATE_INCIDENT,
        target_entity="api-gw-dmz-02.corp.internal",
        target_type="host",
        justification="Escalate unpatched vulnerability to SOC queue"
    )

    # Escalation is PolicyDecision.ALLOW, so it is pre-approved
    if record.status == ActionStatus.WAITING_FOR_APPROVAL:
        approved = policy_engine.approve_action(record.id, approver="Security Operations")
        assert approved.status == ActionStatus.APPROVED
    else:
        assert record.status == ActionStatus.APPROVED

    # Execute simulation
    verified = policy_engine.execute_simulation(record.id)
    assert verified.status == ActionStatus.VERIFIED

    # Check verification details: action-specific, NOT containment
    details = verified.verification_details.lower()
    assert "ticket" in details or "ticketing" in details
    assert "containment" not in details
    assert "vlan" not in details
    assert "isolated" not in details


def test_action_verification_is_strictly_action_specific():
    """
    Verify each of the 4 supported action types produces distinct, action-specific verification feedback.
    """
    actions = [
        (ResponseActionType.SIMULATE_ISOLATE_HOST, "host-jump-prod-01", "host", "isolated VLAN"),
        (ResponseActionType.SIMULATE_DISABLE_ACCOUNT, "id-jdoe", "identity", "marked disabled"),
        (ResponseActionType.SIMULATE_BLOCK_INDICATOR, "ind-c2-ip", "indicator", "firewall rule applied"),
        (ResponseActionType.SIMULATE_ESCALATE_INCIDENT, "host-jump-prod-01", "host", "ticketing check"),
    ]

    for action_type, target_entity, target_type, expected_keyword in actions:
        rec = policy_engine.propose_action(action_type, target_entity, target_type, "Action verification test")
        if rec.status == ActionStatus.WAITING_FOR_APPROVAL:
            rec = policy_engine.approve_action(rec.id)
        verified = policy_engine.execute_simulation(rec.id)
        assert verified.status == ActionStatus.VERIFIED
        assert expected_keyword in verified.verification_details


def test_simulated_fleet_state_survives_restart():
    """
    Requirement 10: Simulated host isolation, account disablement, and indicator blocking
    must survive application restarts.
    """
    from backend.policy import SimulatedEnvironment

    # 1. Propose, approve, and execute host isolation
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_ISOLATE_HOST,
        target_entity="host-jump-prod-01",
        target_type="host",
        justification="Restart durability test"
    )
    policy_engine.approve_action(record.id)
    verified = policy_engine.execute_simulation(record.id)
    assert verified.status == ActionStatus.VERIFIED
    assert simulated_env.hosts["host-jump-prod-01"]["network_state"] == "isolated"

    # 2. Simulate process restart by instantiating a completely fresh SimulatedEnvironment
    restarted_env = SimulatedEnvironment(auto_load=True)

    # 3. Verify state reloaded successfully
    reloaded_action = restarted_env.get_action(record.id)
    assert reloaded_action is not None
    assert reloaded_action.status == ActionStatus.VERIFIED
    assert reloaded_action.target_entity == "host-jump-prod-01"
    assert "isolated VLAN" in reloaded_action.verification_details

    # 4. Verify simulated host reflects durable isolated state
    assert restarted_env.hosts["host-jump-prod-01"]["network_state"] == "isolated"
    assert restarted_env.hosts["host-jump-prod-01"]["isolated"] is True


def test_unapproved_action_remains_unapproved_across_restart():
    """
    Requirement 10: A restart must not turn an unapproved action into an approved action.
    """
    from backend.policy import SimulatedEnvironment

    # Propose consequential action that requires approval
    record = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_DISABLE_ACCOUNT,
        target_entity="id-jdoe",
        target_type="identity",
        justification="Pending review"
    )
    assert record.status == ActionStatus.WAITING_FOR_APPROVAL

    # Simulate process restart
    restarted_env = SimulatedEnvironment(auto_load=True)
    reloaded = restarted_env.get_action(record.id)

    assert reloaded is not None
    assert reloaded.status == ActionStatus.WAITING_FOR_APPROVAL
    assert reloaded.approved_at is None
    # Account must still be active
    assert restarted_env.accounts["id-jdoe"]["status"] == "active"
    assert restarted_env.accounts["id-jdoe"]["disabled"] is False


def test_session_isolated_simulation_state():
    """
    Requirement 10: Multi-user session isolation prevents one judge's actions
    from corrupting another judge's investigation experience.
    """
    session_alpha = "judge-session-alpha"
    session_beta = "judge-session-beta"

    # Judge Alpha isolates host-auth-portal-01
    rec_alpha = policy_engine.propose_action(
        action_type=ResponseActionType.SIMULATE_ISOLATE_HOST,
        target_entity="host-auth-portal-01",
        target_type="host",
        justification="Judge Alpha test",
        session_id=session_alpha
    )
    policy_engine.approve_action(rec_alpha.id)
    verified_alpha = policy_engine.execute_simulation(rec_alpha.id)
    assert verified_alpha.status == ActionStatus.VERIFIED

    # In Judge Alpha's session, host is isolated
    host_alpha = simulated_env.get_host("host-auth-portal-01", session_id=session_alpha)
    assert host_alpha["network_state"] == "isolated"
    assert host_alpha["isolated"] is True

    # In Judge Beta's session, host remains unisolated and active
    host_beta = simulated_env.get_host("host-auth-portal-01", session_id=session_beta)
    assert host_beta["network_state"] == "connected"
    assert host_beta["isolated"] is False

