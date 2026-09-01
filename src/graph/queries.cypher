// Question: Which suppliers dominate multiple flagship products, and what segment revenue relies on them?
MATCH (supp:Organization)-[:MANUFACTURES|SUPPLIES]->(c:Component)<-[:USES_COMPONENT]-(p:Product)
MATCH (p)-[:BELONGS_TO_LINE]->(line:Product)<-[:PRODUCES]-(brand:Organization)
OPTIONAL MATCH (brand)-[rev:PRODUCES]->(line)
RETURN
    supp.name AS Supplier,
    collect(DISTINCT c.name) AS CriticalComponents,
    collect(DISTINCT p.name) AS DependentProducts,
    line.name AS ProductLine,
    rev.revenue_usd_millions AS AtRiskLineRevenueMillions
ORDER BY size(DependentProducts) DESC;