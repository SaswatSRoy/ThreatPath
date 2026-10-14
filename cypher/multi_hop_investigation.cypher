// Query 2: Multi-Hop Evidence & Attack Path Traversal
// Traces causal chain from Alert to Host, executed Process, and external C2 Indicator.

MATCH p = (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:EXECUTED]->(pr:Process)-[:CONNECTED_TO]->(ind:Indicator)
WHERE a.id = $alert_id
RETURN p;
