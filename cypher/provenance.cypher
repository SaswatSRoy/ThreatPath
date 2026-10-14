// Query 7: Investigation Provenance & Audit Trail
// Persists the investigation outcome and links it to the Alert and Response Action.

MATCH (a:Alert)
WHERE a.id = $alert_id
MERGE (inv:Investigation {id: $inv_id})
SET inv.started_at = $started_at,
    inv.completed_at = $completed_at,
    inv.classification = $classification,
    inv.priority = $priority,
    inv.raw_score = $raw_score,
    inv.narrative = $narrative
MERGE (inv)-[:INVESTIGATES]->(a)
RETURN inv;
