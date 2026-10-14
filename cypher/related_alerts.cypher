// Query 3: Finding Related Alerts Through Shared Entities
// Correlates alerts that pivot on identical Host, Identity, or external Indicator.

MATCH (a1:Alert)-[:HAS_EVENT]->(e1:Event)
WHERE a1.id = $alert_id
OPTIONAL MATCH (e1)-[:OCCURRED_ON]->(h:Host)<-[:OCCURRED_ON]-(e2:Event)<-[:HAS_EVENT]-(a2:Alert)
WHERE a1.id <> a2.id
OPTIONAL MATCH (e1)-[:INVOLVES_IDENTITY]->(i:Identity)<-[:INVOLVES_IDENTITY]-(e3:Event)<-[:HAS_EVENT]-(a3:Alert)
WHERE a1.id <> a3.id
RETURN a1, a2, h, a3, i;
