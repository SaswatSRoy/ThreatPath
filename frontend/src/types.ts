export type CompromiseClassification = 'insufficient_evidence' | 'suspicious' | 'likely_compromise';
export type RemediationPriority = 'low' | 'medium' | 'high' | 'critical';
export type PolicyDecision = 'ALLOW' | 'REQUIRE_APPROVAL' | 'BLOCK';
export type ActionStatus = 'PROPOSED' | 'VALIDATED' | 'WAITING_FOR_APPROVAL' | 'APPROVED' | 'EXECUTING' | 'VERIFYING' | 'VERIFIED' | 'FAILED' | 'UNVERIFIED' | 'DENIED' | 'CANCELLED';

export interface AlertSummary {
  id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  timestamp: string;
  source: string;
  alert_type: string;
  target_host?: string;
  target_identity?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  category: string;
  properties: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  properties: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ScoreFactor {
  factor_name: string;
  weight: number;
  description: string;
  evidence_ids: string[];
}

export interface Assessment {
  classification: CompromiseClassification;
  raw_score: number;
  remediation_priority: RemediationPriority;
  score_factors: ScoreFactor[];
  supporting_evidence_ids: string[];
  contradictory_evidence_ids: string[];
  missing_evidence: string[];
  relevant_graph_paths: string[];
  uncertainty_explanation: string;
}

export interface ResponseActionRecord {
  id: string;
  action_type: string;
  target_entity: string;
  target_type: string;
  justification: string;
  policy_decision: PolicyDecision;
  status: ActionStatus;
  proposed_at: string;
  approved_at?: string;
  executed_at?: string;
  verified_at?: string;
  verification_details?: string;
  investigation_id?: string;
}

export interface InvestigationRecord {
  id: string;
  alert_id: string;
  started_at: string;
  completed_at?: string;
  status: string;
  mode: string;
  assessment: Assessment;
  narrative: string;
  graph: GraphData;
  recommended_action?: ResponseActionRecord;
  provenance_path_count: number;
}

export interface SystemHealth {
  status: string;
  falkordb_status: string;
  active_graph: string;
  available_graphs: string[];
  llm_mode: string;
  simulated_responses_enabled: boolean;
}

export interface ValidationErrorItem {
  field: string;
  message: string;
  code: string;
}

export interface ScenarioValidationResponse {
  valid: boolean;
  errors: ValidationErrorItem[];
  warnings: string[];
  preview?: GraphData | null;
}

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string;
  alert_id: string;
  alert_title: string;
  severity: string;
  created_at: string;
  node_count: number;
  relationship_count: number;
  session_id: string;
}

export interface ScenarioDetails extends ScenarioSummary {
  payload: Record<string, any>;
}
