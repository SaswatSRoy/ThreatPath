// Query 1: Alert Context & Connected Events
// Retrieves the core incident envelope: Alert, connected Event, target Host, and Identity.

MATCH (a:Alert)
WHERE a.id = $alert_id
OPTIONAL MATCH (a)-[:HAS_EVENT]->(e:Event)
OPTIONAL MATCH (e)-[:OCCURRED_ON]->(h:Host)
OPTIONAL MATCH (e)-[:INVOLVES_IDENTITY]->(i:Identity)
RETURN a, e, h, i;
