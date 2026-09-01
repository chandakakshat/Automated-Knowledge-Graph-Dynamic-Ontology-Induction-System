"""
run_direct.py - Self-contained runner that executes all assessment steps
"""
import os
import sys
import json
from src.acquisition.ingest import DataIngestionPipeline
from src.extraction.triples import TripleExtractor
from src.ontology.engine import DynamicOntologyManager
from src.graph.neo4j_loader import Neo4jPipeline

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PWD = os.getenv("NEO4J_PASSWORD", "industrial_kg_password")

def execute():
    print("=" * 60)
    print("1. RUNNING INGESTION RUN 1 (Cold Start)")
    print("=" * 60)
    ingestor = DataIngestionPipeline()
    docs1 = ingestor.load_run("run_1")
    print(f"Loaded {len(docs1)} document chunks from Run 1.")

    extractor = TripleExtractor()
    triples1 = extractor.extract_triples(docs1)
    print(f"Extracted {len(triples1)} relational triples:")
    for t in triples1[:3]:
        print(f"  -> ({t['subject']}) -[{t['pred']}]-> ({t['object']})")

    ontology = DynamicOntologyManager()
    ontology.update_from_triples(triples1)
    ontology.save()
    print("Saved induced schema to src/ontology/schema_store.json")

    print(f"Connecting to Neo4j at {URI}...")
    try:
        db = Neo4jPipeline(URI, USER, PWD)
        db.init_constraints()
        db.load_triples(triples1)
        print("Run 1 loaded into Neo4j successfully.")
    except Exception as e:
        print(f"[Neo4j Error]: {e}")
        print("Tip: If running locally without Neo4j, set up free AuraDB or check database connection.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("2. RUNNING INGESTION RUN 2 (Self-Learning & Evolution)")
    print("=" * 60)
    docs2 = ingestor.load_run("run_2")
    triples2 = extractor.extract_triples(docs2)
    print(f"Extracted {len(triples2)} new triples from Run 2.")

    ontology.update_from_triples(triples2)
    ontology.save()
    print(f"Schema evolved. Surfaced conflicts/expansions: {len(ontology.conflicts)}")
    for c in ontology.conflicts:
        print(f"  [Conflict/Evolution] {c['relation']} -> {c['type']}")

    db.load_triples(triples2)
    db.close()
    print("Run 2 loaded into Neo4j successfully.")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED! Launch UI with:")
    print("streamlit run src/visualization/app.py")
    print("=" * 60)

if __name__ == "__main__":
    execute()