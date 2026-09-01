"""
src/visualization/app.py
Cross-platform Streamlit UI with robust in-memory Pyvis rendering.
"""

import json
import os
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from neo4j import GraphDatabase
from pyvis.network import Network

st.set_page_config(layout="wide", page_title="Industrial Knowledge Graph Explorer")
st.title("Industrial Context Graph & Dynamic Ontology Explorer")

# Anchor paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "src" / "ontology" / "schema_store.json"

mode = st.sidebar.radio(
    "Select Visualization View",
    ["Instance Graph (Entities)", "Ontology Schema (Types & Confidence)"]
)

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "industrial_kg_password")

if mode == "Instance Graph (Entities)":
    st.subheader("Instance Context Graph (Cross-Source Entities)")

    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        net = Network(height="650px", width="100%", bgcolor="#222222", font_color="white", directed=True)
        net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -4000,
              "springLength": 120
            }
          }
        }
        """)

        with driver.session() as session:
            result = session.run(
                "MATCH (n)-[r]->(m) "
                "RETURN n.name AS s, coalesce(labels(n)[0], 'Entity') AS s_label, "
                "type(r) AS rel, m.name AS o, coalesce(labels(m)[0], 'Entity') AS o_label "
                "LIMIT 250"
            )
            records = list(result)

            if not records:
                st.warning("No data found in Neo4j. Run `python run_direct.py` first.")
            else:
                for row in records:
                    s_name = str(row["s"] or "Unknown")
                    o_name = str(row["o"] or "Unknown")
                    s_label = str(row["s_label"])
                    o_label = str(row["o_label"])
                    rel_type = str(row["rel"] or "RELATED_TO")

                    net.add_node(s_name, label=s_name, group=s_label, title=f"Type: {s_label}")
                    net.add_node(o_name, label=o_name, group=o_label, title=f"Type: {o_label}")
                    net.add_edge(s_name, o_name, title=rel_type, label=rel_type)

                html_string = net.generate_html()
                components.html(html_string, height=700, scrolling=True)

        driver.close()
    except Exception as e:
        st.error(f"Error loading Instance Graph: {e}")

elif mode == "Ontology Schema (Types & Confidence)":
    st.subheader("Generated Ontology Schema Layer")

    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)

        col1, col2 = st.columns([3, 1])

        with col1:
            net = Network(height="650px", width="100%", bgcolor="#1a1a1a", font_color="white", directed=True)
            net.set_options("""
            var options = {
              "physics": {
                "barnesHut": {
                  "gravitationalConstant": -6000,
                  "springLength": 180
                }
              }
            }
            """)

            for rel_name, data in schema.get("relations", {}).items():
                for d in data.get("domains", []):
                    for r in data.get("ranges", []):
                        conf = data.get("confidence", 0.0)
                        ev = data.get("evidence_count", 0)

                        net.add_node(d, label=d, color="#00adb5", shape="box", font={"color": "white", "size": 16})
                        net.add_node(r, label=r, color="#ff5722", shape="box", font={"color": "white", "size": 16})
                        net.add_edge(
                            d, r,
                            label=f"{rel_name} ({conf})",
                            title=f"Relation: {rel_name}<br>Confidence: {conf}<br>Evidence: {ev}",
                            color={"color": "#aaaaaa"}
                        )

            html_string = net.generate_html()
            components.html(html_string, height=700, scrolling=True)

        with col2:
            st.write("### Schema Metrics")
            st.metric("Induced Classes", len(schema.get("classes", {})))
            st.metric("Induced Predicates", len(schema.get("relations", {})))

            st.write("#### Class Confidences")
            for c_name, c_meta in schema.get("classes", {}).items():
                st.text(f"{c_name}: conf={c_meta.get('confidence')} (n={c_meta.get('evidence_count')})")

            st.write("#### Surfaced Schema Mutations:")
            conflicts = schema.get("detected_conflicts", [])
            if conflicts:
                for c in conflicts:
                    st.warning(f"`{c.get('relation')}` -> `{c.get('type')}`")
            else:
                st.success("No schema collisions detected.")
    else:
        st.info(f"Schema file not found at: `{SCHEMA_PATH}`. Run `python run_direct.py` first.")