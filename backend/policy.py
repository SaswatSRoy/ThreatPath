"""
Response Policy, Approval Gate, and Simulated Execution & Verification Engine
Ensures no real-world destructive actions can ever occur.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.models import (
    PolicyDecision,
    ActionStatus,
    ResponseActionType,
    ResponseActionRecord
)

logger = logging.getLogger(__name__)


class SimulatedEnvironment:
    """
    Maintains simulated infrastructure state with verifiable outcomes.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.hosts = {
            "host-jump-prod-01": {"hostname": "jump-prod-01.corp.internal", "network_state": "connected", "isolated": False, "environment": "production"},
            "host-auth-portal-01": {"hostname": "auth-gateway.corp.internal", "network_state": "connected", "isolated": False, "environment": "production"},
            "host-web-dmz-02": {"hostname": "api-gw-dmz-02.corp.internal", "network_state": "connected", "isolated": False, "environment": "dmz"},
            "host-stage-bastion": {"hostname": "bastion-stage.corp.internal", "network_state": "connected", "isolated": False, "environment": "staging"}
        }
        self.accounts = {
            "id-jdoe": {"username": "jdoe", "status": "active", "disabled": False},
            "id-mchen": {"username": "mchen", "status": "active", "disabled": False}
        }
        self.indicators = {
            "ind-c2-ip": {"value": "198.51.100.44", "perimeter_blocked": False},
            "ind-unrelated-scanner": {"value": "203.0.113.88", "perimeter_blocked": False}
        }
        self.actions: Dict[str, ResponseActionRecord] = {}


simulated_env = SimulatedEnvironment()


class ResponsePolicyEngine:
    """
    Deterministic security policy: determines whether simulated action requires human approval.
    """

    @staticmethod
    def evaluate_policy(action_type: ResponseActionType, target_entity: str) -> PolicyDecision:
        # Isolating production hosts or disabling accounts is high-impact -> REQUIRE_APPROVAL
        if action_type in [ResponseActionType.SIMULATE_ISOLATE_HOST, ResponseActionType.SIMULATE_DISABLE_ACCOUNT]:
            return PolicyDecision.REQUIRE_APPROVAL
        
        # Blocking an external indicator or escalating an incident can be automated
        if action_type in [ResponseActionType.SIMULATE_BLOCK_INDICATOR, ResponseActionType.SIMULATE_ESCALATE_INCIDENT]:
            return PolicyDecision.ALLOW

        return PolicyDecision.BLOCK

    @staticmethod
    def propose_action(
        action_type: ResponseActionType,
        target_entity: str,
        target_type: str,
        justification: str,
        investigation_id: Optional[str] = None
    ) -> ResponseActionRecord:
        action_id = f"act-{uuid.uuid4().hex[:8]}"
        policy_decision = ResponsePolicyEngine.evaluate_policy(action_type, target_entity)
        now_str = datetime.now(timezone.utc).isoformat()

        status = ActionStatus.WAITING_FOR_APPROVAL if policy_decision == PolicyDecision.REQUIRE_APPROVAL else ActionStatus.APPROVED

        record = ResponseActionRecord(
            id=action_id,
            action_type=action_type,
            target_entity=target_entity,
            target_type=target_type,
            justification=justification,
            policy_decision=policy_decision,
            status=status,
            proposed_at=now_str,
            investigation_id=investigation_id
        )
        simulated_env.actions[action_id] = record
        return record

    @staticmethod
    def approve_action(action_id: str, approver: str = "Security Analyst") -> ResponseActionRecord:
        record = simulated_env.actions.get(action_id)
        if not record:
            raise ValueError(f"Action '{action_id}' not found")
        if record.status != ActionStatus.WAITING_FOR_APPROVAL:
            raise ValueError(f"Action '{action_id}' is in state '{record.status}', cannot approve")

        record.status = ActionStatus.APPROVED
        record.approved_at = datetime.now(timezone.utc).isoformat()
        return record

    @staticmethod
    def deny_action(action_id: str, reason: str, approver: str = "Security Analyst") -> ResponseActionRecord:
        record = simulated_env.actions.get(action_id)
        if not record:
            raise ValueError(f"Action '{action_id}' not found")
        if record.status != ActionStatus.WAITING_FOR_APPROVAL:
            raise ValueError(f"Action '{action_id}' is in state '{record.status}', cannot deny")

        record.status = ActionStatus.DENIED
        record.verification_details = f"Denied by {approver}: {reason}"
        return record

    @staticmethod
    def execute_simulation(action_id: str) -> ResponseActionRecord:
        record = simulated_env.actions.get(action_id)
        if not record:
            raise ValueError(f"Action '{action_id}' not found")
        
        # Enforce approval gate!
        if record.status != ActionStatus.APPROVED:
            raise PermissionError(
                f"Policy Gate Enforced: Action '{action_id}' must be APPROVED before execution. Current status: '{record.status}'"
            )

        record.status = ActionStatus.EXECUTING
        now_str = datetime.now(timezone.utc).isoformat()
        record.executed_at = now_str

        # Perform state mutation in the simulated environment
        if record.action_type == ResponseActionType.SIMULATE_ISOLATE_HOST:
            host = simulated_env.hosts.get(record.target_entity)
            if host:
                host["network_state"] = "isolated"
                host["isolated"] = True
                record.status = ActionStatus.VERIFYING
            else:
                record.status = ActionStatus.FAILED
                record.verification_details = f"Target host '{record.target_entity}' not found in simulated fleet."
                return record

        elif record.action_type == ResponseActionType.SIMULATE_DISABLE_ACCOUNT:
            account = simulated_env.accounts.get(record.target_entity)
            if account:
                account["status"] = "disabled"
                account["disabled"] = True
                record.status = ActionStatus.VERIFYING
            else:
                record.status = ActionStatus.FAILED
                record.verification_details = f"Target identity '{record.target_entity}' not found."
                return record

        elif record.action_type == ResponseActionType.SIMULATE_BLOCK_INDICATOR:
            ind = simulated_env.indicators.get(record.target_entity)
            if ind:
                ind["perimeter_blocked"] = True
                record.status = ActionStatus.VERIFYING
            else:
                record.status = ActionStatus.FAILED
                record.verification_details = f"Target indicator '{record.target_entity}' not found."
                return record

        elif record.action_type == ResponseActionType.SIMULATE_ESCALATE_INCIDENT:
            record.status = ActionStatus.VERIFYING

        # Automatically trigger verification
        return ResponsePolicyEngine.verify_simulation(action_id)

    @staticmethod
    def verify_simulation(action_id: str) -> ResponseActionRecord:
        record = simulated_env.actions.get(action_id)
        if not record:
            raise ValueError(f"Action '{action_id}' not found")

        now_str = datetime.now(timezone.utc).isoformat()
        record.verified_at = now_str

        if record.action_type == ResponseActionType.SIMULATE_ISOLATE_HOST:
            host = simulated_env.hosts.get(record.target_entity)
            if host and host.get("network_state") == "isolated" and host.get("isolated") is True:
                record.status = ActionStatus.VERIFIED
                record.verification_details = f"Simulated telemetry check: Host '{host['hostname']}' network interface placed in isolated VLAN; traffic restricted."
            else:
                record.status = ActionStatus.UNVERIFIED
                record.verification_details = "Verification failed: Host state did not transition to isolated."

        elif record.action_type == ResponseActionType.SIMULATE_DISABLE_ACCOUNT:
            account = simulated_env.accounts.get(record.target_entity)
            if account and account.get("status") == "disabled" and account.get("disabled") is True:
                record.status = ActionStatus.VERIFIED
                record.verification_details = f"Simulated directory check: Account '{account['username']}' marked disabled and active sessions terminated."
            else:
                record.status = ActionStatus.UNVERIFIED
                record.verification_details = "Verification failed: Account status was not disabled."

        elif record.action_type == ResponseActionType.SIMULATE_BLOCK_INDICATOR:
            ind = simulated_env.indicators.get(record.target_entity)
            if ind and ind.get("perimeter_blocked") is True:
                record.status = ActionStatus.VERIFIED
                record.verification_details = f"Simulated boundary check: Edge firewall rule applied for {ind['value']}; ingress/egress dropped."
            else:
                record.status = ActionStatus.UNVERIFIED
                record.verification_details = "Verification failed: Perimeter block not confirmed."

        elif record.action_type == ResponseActionType.SIMULATE_ESCALATE_INCIDENT:
            record.status = ActionStatus.VERIFIED
            record.verification_details = "Simulated ticketing check: Incident dispatch ticket generated with high priority."

        return record


policy_engine = ResponsePolicyEngine()
