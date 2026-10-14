// Query 4: Checking Critical Asset Exposure
// Checks whether any host involved in the alert has network or access privileges to high-value assets.

MATCH p = (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:CAN_ACCESS]->(ast:Asset)
WHERE a.id = $alert_id
RETURN p, h.hostname AS hostname, ast.name AS asset_name, ast.criticality AS criticality, ast.data_classification AS classification;
