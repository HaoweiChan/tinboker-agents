import hashlib
import re
from datetime import datetime

from extract.base import Extractor
from graph.models import Edge, Evidence
from ingest.models import RawDoc


PATTERNS = {
    "SUPPLIES": [
        r"(\w+(?:\s+\w+)*)\s+supplies\s+(\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*)\s+provides\s+(\w+(?:\s+\w+)*)\s+to\s+(\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*)\s+is\s+a\s+supplier\s+of\s+(\w+(?:\s+\w+)*)",
    ],
    "PARTNERS_WITH": [
        r"(\w+(?:\s+\w+)*)\s+partners?\s+with\s+(\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*)\s+and\s+(\w+(?:\s+\w+)*)\s+collaborat",
        r"(\w+(?:\s+\w+)*)\s+teams?\s+up\s+with\s+(\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*)\s+joins?\s+forces?\s+with\s+(\w+(?:\s+\w+)*)",
    ],
    "INVESTS_IN": [
        r"(\w+(?:\s+\w+)*)\s+invests?\s+in\s+(\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*)\s+funding\s+(\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*)\s+backed\s+(\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*)\s+funds?\s+(\w+(?:\s+\w+)*)",
    ],
}


class PatternRelationExtractor(Extractor):
    name = "pattern_relations"

    def __init__(self):
        self.compiled_patterns = {}
        for rel_type, patterns in PATTERNS.items():
            self.compiled_patterns[rel_type] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def extract(self, doc: RawDoc) -> tuple[list, list[Edge], list[Evidence]]:
        edges = []
        evidence_list = []

        sentences = self._split_sentences(doc.text)

        for sentence in sentences:
            for rel_type, patterns in self.compiled_patterns.items():
                for pattern in patterns:
                    matches = pattern.finditer(sentence)
                    for match in matches:
                        groups = match.groups()
                        if len(groups) >= 2:
                            src = groups[0].strip()
                            dst = groups[-1].strip()

                            if self._is_valid_entity(src) and self._is_valid_entity(dst):
                                edge_id = f"{src}:{rel_type}:{dst}"
                                edge = Edge(
                                    src=self._normalize_entity_id(src),
                                    dst=self._normalize_entity_id(dst),
                                    rel=rel_type,
                                    props={},
                                )

                                snippet = sentence[max(0, match.start() - 50) : match.end() + 50]
                                evidence_id = self._generate_evidence_id(doc, snippet, match.start())

                                evidence = Evidence(
                                    id=evidence_id,
                                    source=doc.url,
                                    published_at=doc.published_at,
                                    snippet=snippet,
                                    extractor=self.name,
                                    confidence=0.7,
                                    hash=self._compute_hash(snippet),
                                    sentence_span=(match.start(), match.end()),
                                )

                                edges.append(edge)
                                evidence_list.append(evidence)

        return [], edges, evidence_list

    def _split_sentences(self, text: str) -> list[str]:
        sentence_endings = re.compile(r"[.!?]+")
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

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

