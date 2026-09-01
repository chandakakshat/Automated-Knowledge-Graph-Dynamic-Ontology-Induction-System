"""
src/ontology/engine.py
Dynamic ontology induction, asymptotic confidence scoring, and conflict tracking.
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


class DynamicOntologyManager:
    def __init__(self, schema_file: str = None):
        if schema_file is not None:
            self.schema_file = Path(schema_file)
        else:
            # Anchors directly to Avathon/src/ontology/schema_store.json
            project_root = Path(__file__).resolve().parents[2]
            self.schema_file = project_root / "src" / "ontology" / "schema_store.json"

        self.classes = defaultdict(lambda: {"evidence_count": 0, "confidence": 0.0, "source_contexts": set()})
        self.relations = defaultdict(lambda: {"domains": set(), "ranges": set(), "evidence_count": 0, "confidence": 0.0})
        self.conflicts = []
        self._load()

    def _load(self):
        if self.schema_file.exists():
            try:
                with open(self.schema_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for c, meta in data.get("classes", {}).items():
                        self.classes[c] = {
                            "evidence_count": meta["evidence_count"],
                            "confidence": meta["confidence"],
                            "source_contexts": set(meta.get("source_contexts", []))
                        }
                    for r, meta in data.get("relations", {}).items():
                        self.relations[r] = {
                            "domains": set(meta["domains"]),
                            "ranges": set(meta["ranges"]),
                            "evidence_count": meta["evidence_count"],
                            "confidence": meta["confidence"]
                        }
                    self.conflicts = data.get("detected_conflicts", [])
            except Exception:
                pass

    def save(self):
        self.schema_file.parent.mkdir(parents=True, exist_ok=True)
        export = {
            "classes": {
                k: {
                    "evidence_count": v["evidence_count"],
                    "confidence": round(v["confidence"], 3),
                    "source_contexts": list(v["source_contexts"])
                }
                for k, v in self.classes.items()
            },
            "relations": {
                k: {
                    "domains": list(v["domains"]),
                    "ranges": list(v["ranges"]),
                    "evidence_count": v["evidence_count"],
                    "confidence": round(v["confidence"], 3)
                }
                for k, v in self.relations.items()
            },
            "detected_conflicts": self.conflicts
        }
        with open(self.schema_file, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2)

    def update_from_triples(self, triples: List[Dict[str, Any]]):
        """
        Dynamically updates ontology classes, relation domains/ranges,
        and asymptotic confidence scores from extracted triples.
        """
        for fact in triples:
            s_type = fact.get("s_type", "Concept")
            o_type = fact.get("o_type", "Concept")
            pred = fact.get("pred", "RELATED_TO")
            src = fact.get("meta", {}).get("source", "Unknown")

            self._register_class(s_type, src)
            self._register_class(o_type, src)
            self._register_relation(pred, s_type, o_type)

    def _register_class(self, class_name: str, source: str):
        self.classes[class_name]["evidence_count"] += 1
        self.classes[class_name]["source_contexts"].add(source)
        n = self.classes[class_name]["evidence_count"]
        # Asymptotic confidence formula: 1.0 - (1 / (1 + 0.3 * n))
        self.classes[class_name]["confidence"] = 1.0 - (1.0 / (1.0 + (0.3 * n)))

    def _register_relation(self, rel: str, domain: str, range_cls: str):
        rec = self.relations[rel]

        # Check and record dynamic schema domain/range collisions
        if rec["domains"] and domain not in rec["domains"]:
            self.conflicts.append({
                "type": "DOMAIN_EXPANSION_OR_CONFLICT",
                "relation": rel,
                "existing_domains": list(rec["domains"]),
                "new_domain": domain
            })
        if rec["ranges"] and range_cls not in rec["ranges"]:
            self.conflicts.append({
                "type": "RANGE_EXPANSION_OR_CONFLICT",
                "relation": rel,
                "existing_ranges": list(rec["ranges"]),
                "new_range": range_cls
            })

        rec["domains"].add(domain)
        rec["ranges"].add(range_cls)
        rec["evidence_count"] += 1
        # Asymptotic confidence formula for predicates
        rec["confidence"] = 1.0 - (1.0 / (1.0 + (0.25 * rec["evidence_count"])))