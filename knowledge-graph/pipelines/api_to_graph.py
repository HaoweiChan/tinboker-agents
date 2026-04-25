import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from extract.pipeline import ExtractionPipeline
from graph.store.base import GraphStore
from graph.upsert import UpsertManager
from ingest.connectors.base import Connector, FetchQuery
from ingest.normalize import (
    canonicalize_url,
    dedupe_docs,
    filter_by_language,
    normalize_doc_timezone,
)


class APIToGraphPipeline:
    def __init__(
        self,
        connector: Connector,
        extractor_pipeline: ExtractionPipeline,
        graph_store: GraphStore,
        config: dict[str, Any] | None = None,
    ):
        self.connector = connector
        self.extractor_pipeline = extractor_pipeline
        self.graph_store = graph_store
        self.config = config or {}
        self.upsert_manager = UpsertManager(graph_store)

    def run(
        self,
        query: FetchQuery,
        output_dir: Path | None = None,
        checkpoint_dir: Path | None = None,
    ) -> dict[str, Any]:
        stats = {
            "docs_ingested": 0,
            "docs_normalized": 0,
            "entities_extracted": 0,
            "edges_extracted": 0,
            "evidence_extracted": 0,
            "errors": [],
        }

        try:
            docs = list(self.connector.fetch(query))
            stats["docs_ingested"] = len(docs)

            normalized_docs = self._normalize_docs(docs)
            stats["docs_normalized"] = len(normalized_docs)

            if output_dir:
                self._save_docs(normalized_docs, output_dir)

            all_entities = []
            all_edges = []
            all_evidence = []

            for doc in normalized_docs:
                try:
                    entities, edges, evidence = self.extractor_pipeline.extract(doc)
                    all_entities.extend(entities)
                    all_edges.extend(edges)
                    all_evidence.extend(evidence)
                except Exception as e:
                    stats["errors"].append(f"Extraction error for {doc.url}: {str(e)}")

            stats["entities_extracted"] = len(all_entities)
            stats["edges_extracted"] = len(all_edges)
            stats["evidence_extracted"] = len(all_evidence)

            self.upsert_manager.upsert_with_provenance(
                all_entities,
                all_edges,
                all_evidence,
                extractor=self.extractor_pipeline.extractors[0].name if self.extractor_pipeline.extractors else "unknown",
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            stats["errors"].append(f"Pipeline error: {str(e)}")

        return stats

    def _normalize_docs(self, docs: list) -> list:
        normalized = []

        for doc in docs:
            doc.url = canonicalize_url(doc.url)
            doc = normalize_doc_timezone(doc)
            normalized.append(doc)

        if self.config.get("normalization", {}).get("dedupe_enabled", True):
            normalized = dedupe_docs(normalized)

        if self.config.get("normalization", {}).get("language_filter"):
            target_lang = self.config["normalization"]["language_filter"]
            normalized = filter_by_language(normalized, target_lang)

        return normalized

    def _save_docs(self, docs: list, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, doc in enumerate(docs):
            file_path = output_dir / f"doc_{i:06d}.json"
            with open(file_path, "w") as f:
                json.dump(doc.model_dump(), f, default=str, indent=2)

