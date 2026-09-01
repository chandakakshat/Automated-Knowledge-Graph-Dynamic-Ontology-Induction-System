# Automated Knowledge Graph & Dynamic Ontology Induction System

Production-grade pipeline that extracts unstructured multi-source industrial filings, teardowns, and spec sheets into an evolving knowledge graph using Neo4j Community Edition. The system induces its ontology dynamically from grammatical dependency trees without hand-authored schemas, continuously scoring relation confidences and logging domain/range collisions across iterative ingestion runs.

---

## Architecture Overview

* **Data Acquisition (`src/acquisition/ingest.py`)**: Scripted ingestion that normalizes multi-source disclosures (SEC 10-Ks, engineering teardowns, and supplier audit reports).
* **OpenIE Relation Induction (`src/extraction/triples.py`)**: Traverses spaCy dependency parse trees to discover `(Subject, Predicate, Object)` tuples, compound noun structures, and attached numeric/financial attributes dynamically.
* **Dynamic Ontology Engine (`src/ontology/engine.py`)**: Infers class hierarchies and relation domain/range constraints. Calculates Bayesian/asymptotic confidence scores:
  $$\text{Confidence}(e) = 1.0 - \frac{1.0}{1.0 + 0.3 \cdot n}$$
  where $n$ is observation frequency. Flags schema collisions when relations encounter novel domain or range types.
* **Entity Linkage & Resolution (`src/resolution/entity_resolver.py`)**: Resolves naming variances across heterogeneous sources via Jaro-Winkler string similarity and domain alias normalization.
* **Neo4j Loading & Storage (`src/graph/neo4j_loader.py`)**: Merges resolved entities, dynamic predicates, and source provenance into Neo4j Community Edition.
* **Dual-Layer Visualization (`src/visualization/app.py`)**: Interactive Streamlit UI displaying both the Instance Entity Graph and the Meta-Ontology Schema Layer with live confidence metrics[cite: 1].

---

## Project Structure

```text
├── data/
│   └── raw/
│       ├── run_1/              # SEC 10-K, product specs, teardown BOMs
│       └── run_2/              # Delta supplier clean energy audit & evolution reports
├── src/
│   ├── acquisition/ingest.py
│   ├── extraction/triples.py
│   ├── ontology/
│   │   ├── engine.py
│   │   └── schema_store.json   # Exported dynamic schema artifact
│   ├── resolution/entity_resolver.py
│   ├── graph/
│   │   ├── neo4j_loader.py
│   │   └── queries.cypher      # 3 Multi-hop business queries
│   └── visualization/app.py    # Streamlit + Pyvis explorer
├── docker-compose.yml          # Containerized Neo4j Community instance
├── requirements.txt
├── writeup.md                  # 1-page assessment writeup
├── run_direct.py               # Standalone Python runner