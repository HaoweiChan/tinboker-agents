from extract.base import Extractor
from graph.models import Edge, Entity, Evidence
from ingest.models import RawDoc


class ExtractionPipeline:
    def __init__(self, extractors: list[Extractor]):
        self.extractors = extractors

    def extract(self, doc: RawDoc) -> tuple[list[Entity], list[Edge], list[Evidence]]:
        all_entities: dict[str, Entity] = {}
        all_edges: dict[str, Edge] = {}
        all_evidence: list[Evidence] = []

        for extractor in self.extractors:
            entities, edges, evidence = extractor.extract(doc)

            for entity in entities:
                if entity.id not in all_entities:
                    all_entities[entity.id] = entity
                else:
                    existing = all_entities[entity.id]
                    existing.props.update(entity.props)
                    existing.external_ids.update(entity.external_ids)

            for edge in edges:
                edge_key = f"{edge.src}:{edge.rel}:{edge.dst}"
                if edge_key not in all_edges:
                    all_edges[edge_key] = edge
                else:
                    existing = all_edges[edge_key]
                    existing.props.update(edge.props)

            all_evidence.extend(evidence)

        return list(all_entities.values()), list(all_edges.values()), all_evidence

