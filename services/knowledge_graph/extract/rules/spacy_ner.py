import hashlib
from datetime import datetime
from typing import Any

try:
    import spacy
    from spacy.tokens import Doc
except ImportError:
    spacy = None
    Doc = None

from extract.base import Extractor
from graph.models import Entity, Evidence
from ingest.models import RawDoc


LABEL_MAPPING = {
    "PERSON": "Person",
    "ORG": "Organization",
    "GPE": "Place",
    "LOC": "Place",
    "PRODUCT": "Product",
    "MONEY": "Product",
    "EVENT": "Event",
}


class SpacyNERExtractor(Extractor):
    name = "spacy_ner"

    def __init__(self, model_name: str = "en_core_web_sm"):
        if spacy is None:
            raise ImportError("spacy is required. Install with: pip install spacy")
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            raise ImportError(f"spaCy model '{model_name}' not found. Install with: python -m spacy download {model_name}")

    def extract(self, doc: RawDoc) -> tuple[list[Entity], list, list[Evidence]]:
        entities = []
        evidence_list = []

        spacy_doc = self.nlp(doc.text)

        seen_entities: dict[str, Entity] = {}

        for ent in spacy_doc.ents:
            entity_type = LABEL_MAPPING.get(ent.label_, "Entity")

            entity_id = self._generate_entity_id(ent.text, entity_type)

            if entity_id not in seen_entities:
                entity = Entity(
                    id=entity_id,
                    type=entity_type,
                    props={"name": ent.text, "label": ent.label_},
                )
                seen_entities[entity_id] = entity
                entities.append(entity)

            snippet = doc.text[max(0, ent.start_char - 50) : ent.end_char + 50]
            evidence_id = self._generate_evidence_id(doc, snippet, ent.start_char)

            evidence = Evidence(
                id=evidence_id,
                source=doc.url,
                published_at=doc.published_at,
                snippet=snippet,
                extractor=self.name,
                confidence=ent._.score if hasattr(ent._, "score") else 0.8,
                hash=self._compute_hash(snippet),
                sentence_span=(ent.start_char, ent.end_char),
            )
            evidence_list.append(evidence)

        return list(seen_entities.values()), [], evidence_list

    def _generate_entity_id(self, text: str, entity_type: str) -> str:
        normalized = text.lower().strip().replace(" ", "_")
        return f"{entity_type.lower()}:{normalized}"

    def _generate_evidence_id(self, doc: RawDoc, snippet: str, char_offset: int) -> str:
        content = f"{doc.url}{snippet}{char_offset}{self.name}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"evidence:{hash_val}"

    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

