import json
from pathlib import Path
from typing import Any

from extract.base import Extractor
from extract.openie.minie import SimpleOpenIEExtractor
from extract.pipeline import ExtractionPipeline
from extract.rules.patterns import PatternRelationExtractor
from extract.rules.spacy_ner import SpacyNERExtractor
from graph.models import Edge, Entity, Evidence
from ingest.models import RawDoc


class ExtractionService:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._pipelines: dict[str, ExtractionPipeline] = {}

    def get_pipeline(self, pipeline_name: str) -> ExtractionPipeline:
        if pipeline_name not in self._pipelines:
            extractors: list[Extractor] = []

            if "rules" in pipeline_name:
                extractors.append(SpacyNERExtractor())
                extractors.append(PatternRelationExtractor())

            if "openie" in pipeline_name:
                extractors.append(SimpleOpenIEExtractor())

            self._pipelines[pipeline_name] = ExtractionPipeline(extractors)

        return self._pipelines[pipeline_name]

    def extract(
        self,
        docs: list[RawDoc],
        pipeline: str = "rules+openie",
    ) -> tuple[list[Entity], list[Edge], list[Evidence]]:
        extractor_pipeline = self.get_pipeline(pipeline)

        all_entities = []
        all_edges = []
        all_evidence = []

        for doc in docs:
            entities, edges, evidence = extractor_pipeline.extract(doc)
            all_entities.extend(entities)
            all_edges.extend(edges)
            all_evidence.extend(evidence)

        return all_entities, all_edges, all_evidence

    def load_docs_from_dir(self, input_dir: Path) -> list[RawDoc]:
        docs = []
        for file_path in sorted(input_dir.glob("doc_*.json")):
            with open(file_path) as f:
                data = json.load(f)
                docs.append(RawDoc(**data))
        return docs

    def format_output(
        self,
        entities: list[Entity],
        edges: list[Edge],
        evidence: list[Evidence],
        output_format: str = "json",
    ) -> str | dict[str, Any]:
        if output_format == "toon":
            from utils.toon import model_to_toon
            toon_output = []
            for entity in entities:
                toon_output.append(entity.__toon__())
            return "\n".join(toon_output)
        else:
            return {
                "entities": [e.model_dump() for e in entities],
                "edges": [e.model_dump() for e in edges],
                "evidence": [e.model_dump() for e in evidence],
            }

