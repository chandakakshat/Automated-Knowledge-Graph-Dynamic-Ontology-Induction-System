"""
src/graph/neo4j_loader.py
"""
from typing import Any, Dict, List
from neo4j import GraphDatabase, basic_auth
from src.resolution.entity_resolver import EntityResolver


class Neo4jPipeline:
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", pwd: str = "industrial_kg_password"):
        # Explicit basic_auth avoids session token caching bugs
        self.driver = GraphDatabase.driver(
            uri,
            auth=basic_auth(user, pwd),
            max_connection_lifetime=60,
            max_connection_pool_size=50
        )
        self.resolver = EntityResolver()

    def close(self):
        self.driver.close()

    def init_constraints(self):
        with self.driver.session() as s:
            for label in ["Product", "Component", "Organization", "Facility", "Concept"]:
                s.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE;")

    def load_triples(self, triples: List[Dict[str, Any]]):
        with self.driver.session() as session:
            for item in triples:
                canonical_s = self.resolver.resolve(item["subject"], item["s_type"])
                canonical_o = self.resolver.resolve(item["object"], item["o_type"])

                s_id = canonical_s.lower().replace(" ", "_").replace("-", "_")
                o_id = canonical_o.lower().replace(" ", "_").replace("-", "_")

                query = f"""
                MERGE (s:{item['s_type']} {{id: $s_id}})
                ON CREATE SET s.name = $s_name
                MERGE (o:{item['o_type']} {{id: $o_id}})
                ON CREATE SET o.name = $o_name
                MERGE (s)-[r:{item['pred']}]->(o)
                SET r += $props
                """
                session.run(
                    query,
                    s_id=s_id,
                    s_name=canonical_s,
                    o_id=o_id,
                    o_name=canonical_o,
                    props=item.get("meta", {})
                )