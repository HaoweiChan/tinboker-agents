import hashlib
import re
from typing import Any

from extract.base import Extractor
from graph.models import Edge, Evidence
from ingest.models import RawDoc


class SimpleOpenIEExtractor(Extractor):
    name = "simple_openie"

    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence

    def extract(self, doc: RawDoc) -> tuple[list, list[Edge], list[Evidence]]:
        edges = []
        evidence_list = []

        sentences = self._split_sentences(doc.text)

        for sentence in sentences:
            triples = self._extract_triples(sentence)
            for subj, rel, obj, confidence in triples:
                if confidence >= self.min_confidence:
                    edge = Edge(
                        src=self._normalize_entity_id(subj),
                        dst=self._normalize_entity_id(obj),
                        rel=rel.upper().replace(" ", "_"),
                        props={"confidence": confidence},
                    )

                    snippet = sentence
                    evidence_id = self._generate_evidence_id(doc, snippet, 0)

                    evidence = Evidence(
                        id=evidence_id,
                        source=doc.url,
                        published_at=doc.published_at,
                        snippet=snippet,
                        extractor=self.name,
                        confidence=confidence,
                        hash=self._compute_hash(snippet),
                    )

                    edges.append(edge)
                    evidence_list.append(evidence)

        return [], edges, evidence_list

    def _split_sentences(self, text: str) -> list[str]:
        sentence_endings = re.compile(r"[.!?]+")
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_triples(self, sentence: str) -> list[tuple[str, str, str, float]]:
        triples = []

        verb_patterns = [
            (r"(\w+(?:\s+\w+)*)\s+(is|are|was|were)\s+(?:a|an|the)?\s*(\w+(?:\s+\w+)*)", 0.7),
            (r"(\w+(?:\s+\w+)*)\s+(has|have|had)\s+(?:a|an|the)?\s*(\w+(?:\s+\w+)*)", 0.6),
            (r"(\w+(?:\s+\w+)*)\s+(\w+ed|\w+ing)\s+(?:a|an|the)?\s*(\w+(?:\s+\w+)*)", 0.5),
        ]

        for pattern, confidence in verb_patterns:
            matches = re.finditer(pattern, sentence, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 3:
                    subj = groups[0].strip()
                    rel = groups[1].strip()
                    obj = groups[2].strip()

                    if self._is_valid_entity(subj) and self._is_valid_entity(obj):
                        triples.append((subj, rel, obj, confidence))

        return triples

    def _is_valid_entity(self, text: str) -> bool:
        text = text.strip()
        if len(text) < 2:
            return False
        if text.lower() in {"the", "a", "an", "this", "that", "these", "those"}:
            return False
        return True

    def _normalize_entity_id(self, text: str) -> str:
        normalized = text.lower().strip().replace(" ", "_")
        return f"entity:{normalized}"

    def _generate_evidence_id(self, doc: RawDoc, snippet: str, char_offset: int) -> str:
        content = f"{doc.url}{snippet}{char_offset}{self.name}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"evidence:{hash_val}"

    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

