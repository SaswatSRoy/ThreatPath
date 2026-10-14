"""
Response Policy, Approval Gate, and Simulated Execution & Verification Engine
Ensures no real-world destructive actions can ever occur.
Persists simulated fleet mutations and action records durably across restarts.
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from backend.models import (
    PolicyDecision,
    ActionStatus,
    ResponseActionType,
    ResponseActionRecord
)
from backend.config import settings

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_FILE = DATA_DIR / "simulated_state.json"

DEFAULT_HOSTS = {
    "host-jump-prod-01": {"hostname": "jump-prod-01.corp.internal", "network_state": "connected", "isolated": False, "environment": "production"},
    "host-auth-portal-01": {"hostname": "auth-gateway.corp.internal", "network_state": "connected", "isolated": False, "environment": "production"},
    "host-web-dmz-02": {"hostname": "api-gw-dmz-02.corp.internal", "network_state": "connected", "isolated": False, "environment": "dmz"},
    "host-stage-bastion": {"hostname": "bastion-stage.corp.internal", "network_state": "connected", "isolated": False, "environment": "staging"}
}

DEFAULT_ACCOUNTS = {
    "id-jdoe": {"username": "jdoe", "status": "active", "disabled": False},
    "id-mchen": {"username": "mchen", "status": "active", "disabled": False}
}

DEFAULT_INDICATORS = {
    "ind-c2-ip": {"value": "198.51.100.44", "perimeter_blocked": False},
    "ind-unrelated-scanner": {"value": "203.0.113.88", "perimeter_blocked": False}
}


class SimulatedEnvironment:
    """
    Maintains simulated infrastructure state with verifiable outcomes.
    State survives backend restarts and integrates with FalkorDB / durable storage.
    """
    def __init__(self, auto_load: bool = True):
        self.reset(clear_storage=False)
        if auto_load:
            self.load_persisted_state()

    def reset(self, clear_storage: bool = False):
        """
        Reset simulated fleet to baseline.
        If clear_storage is True, durable storage is also purged.
        """
        import copy
        self.hosts = copy.deepcopy(DEFAULT_HOSTS)
        self.accounts = copy.deepcopy(DEFAULT_ACCOUNTS)
        self.indicators = copy.deepcopy(DEFAULT_INDICATORS)
        self.actions: Dict[str, ResponseActionRecord] = {}
        self.session_mutations: Dict[str, Dict[str, Any]] = {}

        if clear_storage:
            self._clear_storage()

    def _clear_storage(self):
        # Clear local state file
        try:
            if STATE_FILE.exists():
                STATE_FILE.unlink()
        except Exception as e:
            logger.debug(f"Could not remove local state file: {e}")

        # Clear FalkorDB state nodes
        try:
            from backend.database import db_manager
            db_manager.execute_query("MATCH (sm:SimulatedState) DELETE sm")
        except Exception as e:
            logger.debug(f"Could not delete SimulatedState nodes from FalkorDB: {e}")

    def _save_local_snapshot(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            snapshot = {
                "hosts": self.hosts,
                "accounts": self.accounts,
                "indicators": self.indicators,
                "session_mutations": self.session_mutations,
                "actions": {k: v.model_dump() for k, v in self.actions.items()}
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save local state snapshot: {e}")

    def persist_action(self, record: ResponseActionRecord, graph_name: Optional[str] = None):
        """
        Persist ResponseActionRecord in memory, FalkorDB, and local snapshot.
        """
        self.actions[record.id] = record
        self._save_local_snapshot()

        # Persist to FalkorDB
        try:
            from backend.database import db_manager
            query = """
            MERGE (ra:ResponseAction {id: $id})
            SET ra.action_type = $action_type,
                ra.target_entity = $target_entity,
                ra.target_type = $target_type,
                ra.justification = $justification,
                ra.policy_decision = $policy_decision,
                ra.status = $status,
                ra.proposed_at = $proposed_at,
                ra.approved_at = $approved_at,
                ra.executed_at = $executed_at,
                ra.verified_at = $verified_at,
                ra.verification_details = $verification_details,
                ra.investigation_id = $investigation_id,
                ra.session_id = $session_id
            """
            params = {
                "id": record.id,
                "action_type": record.action_type.value if hasattr(record.action_type, "value") else str(record.action_type),
                "target_entity": record.target_entity,
                "target_type": record.target_type,
                "justification": record.justification,
                "policy_decision": record.policy_decision.value if hasattr(record.policy_decision, "value") else str(record.policy_decision),
                "status": record.status.value if hasattr(record.status, "value") else str(record.status),
                "proposed_at": record.proposed_at,
                "approved_at": record.approved_at,
                "executed_at": record.executed_at,
                "verified_at": record.verified_at,
                "verification_details": record.verification_details,
                "investigation_id": record.investigation_id,
                "session_id": record.session_id or "demo_default"
            }
            db_manager.execute_query(query, params, graph_name=graph_name)

            if record.investigation_id:
                link_query = """
                MATCH (inv:Investigation {id: $inv_id}), (ra:ResponseAction {id: $ra_id})
                MERGE (inv)-[:RECOMMENDED_ACTION]->(ra)
                """
                db_manager.execute_query(link_query, {"inv_id": record.investigation_id, "ra_id": record.id}, graph_name=graph_name)
        except Exception as e:
            logger.debug(f"Could not persist ResponseAction to FalkorDB: {e}")

    def persist_mutation(
        self,
        session_id: str,
        entity_id: str,
        entity_type: str,
        mutation: Dict[str, Any],
        graph_name: Optional[str] = None
    ):
        """
        Record durable simulated fleet mutation in memory, FalkorDB, and local snapshot.
        """
        sess = session_id or "demo_default"
        if sess not in self.session_mutations:
            self.session_mutations[sess] = {}
        self.session_mutations[sess][entity_id] = mutation
        self._save_local_snapshot()

        # Persist to FalkorDB
        try:
            from backend.database import db_manager
            key = f"{sess}:{entity_id}"
            query = """
            MERGE (sm:SimulatedState {key: $key})
            SET sm.session_id = $session_id,
                sm.entity_id = $entity_id,
                sm.entity_type = $entity_type,
                sm.mutation_json = $mutation_json,
                sm.updated_at = $updated_at
            """
            params = {
                "key": key,
                "session_id": sess,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "mutation_json": json.dumps(mutation),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            db_manager.execute_query(query, params, graph_name=graph_name)
        except Exception as e:
            logger.debug(f"Could not persist SimulatedState to FalkorDB: {e}")

    def load_persisted_state(self, graph_name: Optional[str] = None):
        """
        Load persisted response actions and simulated fleet mutations.
        Attempts FalkorDB first; falls back to local snapshot.
        """
        loaded_from_db = False
        try:
            from backend.database import db_manager
            # 1. Load ResponseAction nodes
            ra_res = db_manager.execute_query(
                """
                MATCH (ra:ResponseAction)
                RETURN ra.id, ra.action_type, ra.target_entity, ra.target_type,
                       ra.justification, ra.policy_decision, ra.status,
                       ra.proposed_at, ra.approved_at, ra.executed_at,
                       ra.verified_at, ra.verification_details, ra.investigation_id,
                       ra.session_id
                """,
                graph_name=graph_name
            )
            for row in ra_res.result_set:
                try:
                    record = ResponseActionRecord(
                        id=row[0],
                        action_type=ResponseActionType(row[1]),
                        target_entity=row[2],
                        target_type=row[3],
                        justification=row[4],
                        policy_decision=PolicyDecision(row[5]),
                        status=ActionStatus(row[6]),
                        proposed_at=row[7],
                        approved_at=row[8],
                        executed_at=row[9],
                        verified_at=row[10],
                        verification_details=row[11],
                        investigation_id=row[12],
                        session_id=row[13] or "demo_default"
                    )
                    self.actions[record.id] = record
                except Exception as ex:
                    logger.debug(f"Error parsing ResponseAction row {row[0]}: {ex}")

            # 2. Load SimulatedState nodes
            sm_res = db_manager.execute_query(
                """
                MATCH (sm:SimulatedState)
                RETURN sm.session_id, sm.entity_id, sm.entity_type, sm.mutation_json
                """,
                graph_name=graph_name
            )
            for row in sm_res.result_set:
                sess_id, ent_id, ent_type, mut_json = row[0], row[1], row[2], row[3]
                try:
                    mutation = json.loads(mut_json)
                    if sess_id not in self.session_mutations:
                        self.session_mutations[sess_id] = {}
                    self.session_mutations[sess_id][ent_id] = mutation

                    # Apply mutation to active default fleet only if demo_default
                    if sess_id == "demo_default":
                        self._apply_mutation_to_fleet(ent_id, ent_type, mutation)
                except Exception as ex:
                    logger.debug(f"Error applying SimulatedState row {ent_id}: {ex}")

            loaded_from_db = True
            logger.info(f"Loaded {len(self.actions)} actions and {len(sm_res.result_set)} mutations from FalkorDB.")
        except Exception as e:
            logger.debug(f"Could not load state from FalkorDB: {e}")

        # Fallback to local snapshot if DB wasn't reachable or empty
        if not loaded_from_db or (len(self.actions) == 0 and STATE_FILE.exists()):
            self._load_local_snapshot()

    def _apply_mutation_to_fleet(self, entity_id: str, entity_type: str, mutation: Dict[str, Any]):
        if entity_type == "host" or entity_id in self.hosts:
            if entity_id in self.hosts:
                self.hosts[entity_id].update(mutation)
        elif entity_type == "identity" or entity_id in self.accounts:
            if entity_id in self.accounts:
                self.accounts[entity_id].update(mutation)
        elif entity_type == "indicator" or entity_id in self.indicators:
            if entity_id in self.indicators:
                self.indicators[entity_id].update(mutation)

    def _load_local_snapshot(self):
        if not STATE_FILE.exists():
            return
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
            if "hosts" in snapshot:
                self.hosts.update(snapshot["hosts"])
            if "accounts" in snapshot:
                self.accounts.update(snapshot["accounts"])
            if "indicators" in snapshot:
                self.indicators.update(snapshot["indicators"])
            if "session_mutations" in snapshot:
                self.session_mutations.update(snapshot["session_mutations"])
            if "actions" in snapshot:
                for k, v in snapshot["actions"].items():
                    if k not in self.actions:
                        self.actions[k] = ResponseActionRecord(**v)
            logger.info(f"Loaded simulated state snapshot from {STATE_FILE}")
        except Exception as e:
            logger.debug(f"Error loading local snapshot: {e}")

    def reapply_persisted_state(self, graph_name: Optional[str] = None):
        """
        Re-apply persisted mutations after graph re-seeding to ensure active state survives seed.
        """
        for sess_id, entities in self.session_mutations.items():
            for ent_id, mutation in entities.items():
                if ent_id in self.hosts:
                    self.hosts[ent_id].update(mutation)
                elif ent_id in self.accounts:
                    self.accounts[ent_id].update(mutation)
                elif ent_id in self.indicators:
                    self.indicators[ent_id].update(mutation)

    def get_action(self, action_id: str) -> Optional[ResponseActionRecord]:
        if action_id in self.actions:
            return self.actions[action_id]
        self.load_persisted_state()
        return self.actions.get(action_id)

    def get_host(self, entity_id: str, session_id: str = "demo_default") -> Optional[Dict[str, Any]]:
        import copy
        if not session_id or session_id == "demo_default":
            return self.hosts.get(entity_id)
        # Custom session: check if session has its own mutation
        if session_id in self.session_mutations and entity_id in self.session_mutations[session_id]:
            base = copy.deepcopy(DEFAULT_HOSTS.get(entity_id, {}))
            base.update(self.session_mutations[session_id][entity_id])
            return base
        return copy.deepcopy(DEFAULT_HOSTS.get(entity_id))

    def get_account(self, entity_id: str, session_id: str = "demo_default") -> Optional[Dict[str, Any]]:
        import copy
        if not session_id or session_id == "demo_default":
            return self.accounts.get(entity_id)
        if session_id in self.session_mutations and entity_id in self.session_mutations[session_id]:
            base = copy.deepcopy(DEFAULT_ACCOUNTS.get(entity_id, {}))
            base.update(self.session_mutations[session_id][entity_id])
            return base
        return copy.deepcopy(DEFAULT_ACCOUNTS.get(entity_id))

    def get_indicator(self, entity_id: str, session_id: str = "demo_default") -> Optional[Dict[str, Any]]:
        import copy
        if not session_id or session_id == "demo_default":
            return self.indicators.get(entity_id)
        if session_id in self.session_mutations and entity_id in self.session_mutations[session_id]:
            base = copy.deepcopy(DEFAULT_INDICATORS.get(entity_id, {}))
            base.update(self.session_mutations[session_id][entity_id])
            return base
        return copy.deepcopy(DEFAULT_INDICATORS.get(entity_id))


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
        investigation_id: Optional[str] = None,
        session_id: str = "demo_default"
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
            investigation_id=investigation_id,
            session_id=session_id
        )
        simulated_env.persist_action(record)
        return record

    @staticmethod
    def approve_action(action_id: str, approver: str = "Security Analyst") -> ResponseActionRecord:
        record = simulated_env.get_action(action_id)
        if not record:
            raise ValueError(f"Action '{action_id}' not found")
        if record.status != ActionStatus.WAITING_FOR_APPROVAL:
            raise ValueError(f"Action '{action_id}' is in state '{record.status}', cannot approve")

        record.status = ActionStatus.APPROVED
        record.approved_at = datetime.now(timezone.utc).isoformat()
        simulated_env.persist_action(record)
        return record

    @staticmethod
    def deny_action(action_id: str, reason: str, approver: str = "Security Analyst") -> ResponseActionRecord:
        record = simulated_env.get_action(action_id)
        if not record:
            raise ValueError(f"Action '{action_id}' not found")
        if record.status != ActionStatus.WAITING_FOR_APPROVAL:
            raise ValueError(f"Action '{action_id}' is in state '{record.status}', cannot deny")

        record.status = ActionStatus.DENIED
        record.verification_details = f"Denied by {approver}: {reason}"
        simulated_env.persist_action(record)
        return record

    @staticmethod
    def execute_simulation(action_id: str) -> ResponseActionRecord:
        record = simulated_env.get_action(action_id)
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
        sess_id = record.session_id or "demo_default"

        # Perform state mutation in the simulated environment
        if record.action_type == ResponseActionType.SIMULATE_ISOLATE_HOST:
            host = simulated_env.get_host(record.target_entity, sess_id)
            if host:
                mutation = {"network_state": "isolated", "isolated": True}
                if sess_id == "demo_default":
                    simulated_env.hosts[record.target_entity].update(mutation)
                simulated_env.persist_mutation(sess_id, record.target_entity, "host", mutation)
                record.status = ActionStatus.VERIFYING
            else:
                record.status = ActionStatus.FAILED
                record.verification_details = f"Target host '{record.target_entity}' not found in simulated fleet."
                simulated_env.persist_action(record)
                return record

        elif record.action_type == ResponseActionType.SIMULATE_DISABLE_ACCOUNT:
            account = simulated_env.get_account(record.target_entity, sess_id)
            if account:
                mutation = {"status": "disabled", "disabled": True}
                if sess_id == "demo_default":
                    simulated_env.accounts[record.target_entity].update(mutation)
                simulated_env.persist_mutation(sess_id, record.target_entity, "identity", mutation)
                record.status = ActionStatus.VERIFYING
            else:
                record.status = ActionStatus.FAILED
                record.verification_details = f"Target identity '{record.target_entity}' not found."
                simulated_env.persist_action(record)
                return record

        elif record.action_type == ResponseActionType.SIMULATE_BLOCK_INDICATOR:
            ind = simulated_env.get_indicator(record.target_entity, sess_id)
            if ind:
                mutation = {"perimeter_blocked": True}
                if sess_id == "demo_default":
                    simulated_env.indicators[record.target_entity].update(mutation)
                simulated_env.persist_mutation(sess_id, record.target_entity, "indicator", mutation)
                record.status = ActionStatus.VERIFYING
            else:
                record.status = ActionStatus.FAILED
                record.verification_details = f"Target indicator '{record.target_entity}' not found."
                simulated_env.persist_action(record)
                return record

        elif record.action_type == ResponseActionType.SIMULATE_ESCALATE_INCIDENT:
            record.status = ActionStatus.VERIFYING
            mutation = {"incident_escalated": True, "escalated_at": now_str}
            simulated_env.persist_mutation(sess_id, record.target_entity, "incident", mutation)

        # Automatically trigger verification
        return ResponsePolicyEngine.verify_simulation(action_id)

    @staticmethod
    def verify_simulation(action_id: str) -> ResponseActionRecord:
        record = simulated_env.get_action(action_id)
        if not record:
            raise ValueError(f"Action '{action_id}' not found")

        now_str = datetime.now(timezone.utc).isoformat()
        record.verified_at = now_str
        sess_id = record.session_id or "demo_default"

        if record.action_type == ResponseActionType.SIMULATE_ISOLATE_HOST:
            host = simulated_env.get_host(record.target_entity, sess_id)
            if host and host.get("network_state") == "isolated" and host.get("isolated") is True:
                record.status = ActionStatus.VERIFIED
                record.verification_details = f"Simulated telemetry check: Host '{host['hostname']}' network interface placed in isolated VLAN; traffic restricted."
            else:
                record.status = ActionStatus.UNVERIFIED
                record.verification_details = "Verification failed: Host state did not transition to isolated."

        elif record.action_type == ResponseActionType.SIMULATE_DISABLE_ACCOUNT:
            account = simulated_env.get_account(record.target_entity, sess_id)
            if account and account.get("status") == "disabled" and account.get("disabled") is True:
                record.status = ActionStatus.VERIFIED
                record.verification_details = f"Simulated directory check: Account '{account['username']}' marked disabled and active sessions terminated."
            else:
                record.status = ActionStatus.UNVERIFIED
                record.verification_details = "Verification failed: Account status was not disabled."

        elif record.action_type == ResponseActionType.SIMULATE_BLOCK_INDICATOR:
            ind = simulated_env.get_indicator(record.target_entity, sess_id)
            if ind and ind.get("perimeter_blocked") is True:
                record.status = ActionStatus.VERIFIED
                record.verification_details = f"Simulated boundary check: Edge firewall rule applied for {ind['value']}; ingress/egress dropped."
            else:
                record.status = ActionStatus.UNVERIFIED
                record.verification_details = "Verification failed: Perimeter block not confirmed."

        elif record.action_type == ResponseActionType.SIMULATE_ESCALATE_INCIDENT:
            record.status = ActionStatus.VERIFIED
            record.verification_details = "Simulated ticketing check: Incident dispatch ticket generated with high priority."

        simulated_env.persist_action(record)
        return record


policy_engine = ResponsePolicyEngine()
