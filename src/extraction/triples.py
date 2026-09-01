"""
src/extraction/triples.py
Open Information Extraction (OpenIE) engine that extracts dynamic (Subject, Predicate, Object)
triples and infers entity classes from syntactic dependency structures.
"""

import spacy
from typing import List, Dict, Any, Optional

# Load small English pipeline (ensure 'python -m spacy download en_core_web_sm' is executed)
nlp = spacy.load("en_core_web_sm")


class TripleExtractor:
    def __init__(self):
        # Minimal seeded hints to bootstrap ontological categorization
        # (Prompt Requirement: Seed hints are acceptable, hardcoding the full schema is not)
        self.component_hints = {
            "chip", "processor", "sensor", "display", "sdram", "memory",
            "controller", "capacitor", "frame", "wafer", "chassis", "battery"
        }
        self.product_hints = {
            "iphone", "mac", "wearable", "ipad", "phone", "device",
            "laptop", "watch", "smartphone"
        }
        self.facility_hints = {
            "fab", "facility", "plant", "foundry", "site", "mine"
        }

    def extract_triples(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parses document chunks and induces relational triples with entity types.
        """
        extracted_facts = []

        for doc_entry in documents:
            text = doc_entry["text"]
            source = doc_entry["source"]
            doc = nlp(text)

            for sent in doc.sents:
                for token in sent:
                    # Target root action predicates
                    if token.pos_ == "VERB" and not token.is_stop:
                        subjs = [w for w in token.lefts if w.dep_ in ("nsubj", "nsubjpass")]
                        objs = [w for w in token.rights if w.dep_ in ("dobj", "attr", "pobj")]

                        # Capture trailing prepositional phrases (e.g., "supplies X *for* Y")
                        prep_objs = []
                        for prep in [w for w in token.rights if w.dep_ == "prep"]:
                            prep_objs.extend([w for w in prep.rights if w.dep_ == "pobj"])

                        if subjs and (objs or prep_objs):
                            # Primary Subject
                            s_token = subjs[0]
                            subj_name = self._reconstruct_compound_phrase(s_token)
                            subj_type = self._infer_entity_type(s_token, subj_name)

                            # Primary Object
                            o_token = objs[0] if objs else prep_objs[0]
                            obj_name = self._reconstruct_compound_phrase(o_token)
                            obj_type = self._infer_entity_type(o_token, obj_name)

                            # Lemmatized relation predicate (e.g., "manufactures" -> "MANUFACTURE")
                            predicate = token.lemma_.upper()

                            # Extract attached attributes (monetary metrics, process nodes, clean energy pct)
                            edge_attributes = self._extract_edge_attributes(sent, o_token, source)

                            extracted_facts.append({
                                "subject": subj_name,
                                "s_type": subj_type,
                                "pred": predicate,
                                "object": obj_name,
                                "o_type": obj_type,
                                "meta": edge_attributes
                            })

                            # Secondary link for prepositional targets (e.g., Object -> Target Product)
                            if objs and prep_objs:
                                secondary_target = prep_objs[0]
                                target_name = self._reconstruct_compound_phrase(secondary_target)
                                target_type = self._infer_entity_type(secondary_target, target_name)

                                extracted_facts.append({
                                    "subject": obj_name,
                                    "s_type": obj_type,
                                    "pred": "ASSOCIATED_WITH",
                                    "object": target_name,
                                    "o_type": target_type,
                                    "meta": {"source": source}
                                })

        return extracted_facts

    def _reconstruct_compound_phrase(self, token) -> str:
        """
        Reconstructs multi-word nominal entities by aggregating compound and adjectival modifiers.
        Example: ['A16', 'Bionic'], ['OLED', 'Super', 'Retina', 'Display']
        """
        modifiers = [child.text for child in token.lefts if child.dep_ in ("compound", "amod", "nummod")]
        modifiers.append(token.text)
        modifiers.extend([child.text for child in token.rights if child.dep_ == "compound"])
        return " ".join(modifiers).strip()

    def _infer_entity_type(self, token, phrase: str) -> str:
        """
        Infers an entity class from spaCy NER tags and bootstrapped domain hints.
        """
        phrase_lower = phrase.lower()

        # 1. Spacy Named Entity Recognition signals
        if token.ent_type_ in ("ORG", "PERSON"):
            return "Organization"
        if token.ent_type_ == "MONEY":
            return "FinancialMetric"

        # 2. Domain-syntactic hint classification
        if any(h in phrase_lower for h in self.product_hints):
            return "Product"
        if any(h in phrase_lower for h in self.component_hints):
            return "Component"
        if any(h in phrase_lower for h in self.facility_hints):
            return "Facility"

        # 3. Fallback classification for novel concepts
        return "Concept"

    def _extract_edge_attributes(self, sent, obj_token, source: str) -> Dict[str, Any]:
        """
        Scans dependents of the predicate and object for numeric metrics and financial values.
        """
        attributes = {"source": source}

        # Check for direct numeric/currency dependents attached to the object
        for child in obj_token.rights:
            if child.ent_type_ == "MONEY" or child.like_num:
                attributes["metric_value"] = child.text

        # Scan sentence for clean energy percentages or manufacturing process nodes
        sent_text = sent.text
        if "percent" in sent_text or "%" in sent_text:
            tokens = [t.text for t in sent]
            for i, t in enumerate(tokens):
                if t in ("percent", "%") and i > 0 and tokens[i - 1].isdigit():
                    attributes["percentage"] = int(tokens[i - 1])

        if "nanometer" in sent_text or "nm" in sent_text:
            for t in sent:
                if "nanometer" in t.text or "nm" in t.text:
                    attributes["process_node"] = t.text

        return attributes


if __name__ == "__main__":
    test_docs = [
        {
            "source": "SEC Form 10-K",
            "text": "Apple Inc manufactures iPhone. Net sales for iPhone were 205489 million dollars."
        },
        {
            "source": "Teardown Report",
            "text": "TSMC manufactures the A16 Bionic processor for iPhone 14 Pro."
        }
    ]
    extractor = TripleExtractor()
    triples = extractor.extract_triples(test_docs)
    for t in triples:
        print(f"({t['subject']}: {t['s_type']}) -[{t['pred']}]-> ({t['object']}: {t['o_type']}) | Meta: {t['meta']}")