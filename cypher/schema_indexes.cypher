// ThreatPath Schema Indexes
// Ensures sub-millisecond lookup on core identifiers across graph traversals.

CREATE INDEX FOR (a:Alert) ON (a.id);
CREATE INDEX FOR (e:Event) ON (e.id);
CREATE INDEX FOR (i:Identity) ON (i.id);
CREATE INDEX FOR (h:Host) ON (h.id);
CREATE INDEX FOR (p:Process) ON (p.id);
CREATE INDEX FOR (ind:Indicator) ON (ind.id);
CREATE INDEX FOR (v:Vulnerability) ON (v.id);
CREATE INDEX FOR (ast:Asset) ON (ast.id);
CREATE INDEX FOR (inv:Investigation) ON (inv.id);
CREATE INDEX FOR (ra:ResponseAction) ON (ra.id);
