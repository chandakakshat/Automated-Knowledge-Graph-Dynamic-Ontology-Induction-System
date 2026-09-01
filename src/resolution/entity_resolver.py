"""
src/resolution/entity_resolver.py
"""
import Levenshtein


class EntityResolver:
    def __init__(self, similarity_threshold=0.82):
        self.registry = {}  # alias -> canonical_id
        self.threshold = similarity_threshold

    def resolve(self, raw_entity_name: str, entity_type: str) -> str:
        name = raw_entity_name.strip()
        cleaned = " ".join(name.lower().split())

        # Hard alias rules for domain abbreviations
        domain_aliases = {
            "tsmc": "Taiwan Semiconductor Manufacturing Company",
            "ti": "Texas Instruments",
            "sony corp": "Sony"
        }
        if cleaned in domain_aliases:
            cleaned = domain_aliases[cleaned].lower()

        # Check existing canonical cluster
        for alias, canonical in self.registry.items():
            score = Levenshtein.jaro_winkler(cleaned, alias.lower())
            if score >= self.threshold:
                self.registry[cleaned] = canonical
                return canonical

        # If novel, declare canonical entity
        self.registry[cleaned] = name
        return name