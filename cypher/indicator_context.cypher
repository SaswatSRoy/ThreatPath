// Query 5: Indicator Context & Network Attribution
// Discovers indicators associated with processes executed on hosts involved in the alert.

MATCH (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:EXECUTED]->(pr:Process)-[:CONNECTED_TO]->(ind:Indicator)
WHERE a.id = $alert_id
RETURN pr.name AS process_name, pr.command_line AS command_line, ind.value AS indicator_value, ind.indicator_type AS indicator_type, ind.reputation AS reputation, ind.malicious_score AS malicious_score;
