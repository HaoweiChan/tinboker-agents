from datetime import datetime

from graph.models import Edge, Entity, Evidence
from graph.store.base import GraphStore


class UpsertManager:
    def __init__(self, store: GraphStore):
        self.store = store

    def upsert_with_provenance(
        self,
        entities: list[Entity],
        edges: list[Edge],
        evidence: list[Evidence],
        extractor: str,
        timestamp: datetime | None = None,
    ) -> None:
        if timestamp is None:
            timestamp = datetime.utcnow()

        merged_entities = self._merge_entities(entities)
        merged_edges = self._merge_edges(edges)
        deduplicated_evidence = self._dedupe_evidence(evidence)

        for ev in deduplicated_evidence:
            ev.extractor = extractor

        self.store.upsert(merged_entities, merged_edges, deduplicated_evidence)

    def _merge_entities(self, entities: list[Entity]) -> list[Entity]:
        merged: dict[str, Entity] = {}

        for entity in entities:
            if entity.id not in merged:
                merged[entity.id] = entity
            else:
                existing = merged[entity.id]
                existing.props.update(entity.props)
                existing.external_ids.update(entity.external_ids)

        return list(merged.values())

    def _merge_edges(self, edges: list[Edge]) -> list[Edge]:
        merged: dict[str, Edge] = {}

        for edge in edges:
            key = f"{edge.src}:{edge.rel}:{edge.dst}"
            if key not in merged:
                merged[key] = edge
            else:
                existing = merged[key]
                existing.props.update(edge.props)

        return list(merged.values())

    def _dedupe_evidence(self, evidence: list[Evidence]) -> list[Evidence]:
        seen_hashes: dict[str, Evidence] = {}

        for ev in evidence:
            if ev.hash:
                if ev.hash not in seen_hashes:
                    seen_hashes[ev.hash] = ev
            else:
                seen_hashes[ev.id] = ev

        return list(seen_hashes.values())

