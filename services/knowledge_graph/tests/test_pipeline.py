from datetime import datetime

import pytest
from pydantic import HttpUrl

from extract.openie.minie import SimpleOpenIEExtractor
from extract.pipeline import ExtractionPipeline
from extract.rules.patterns import PatternRelationExtractor
from extract.rules.spacy_ner import SpacyNERExtractor
from ingest.models import RawDoc


@pytest.fixture
def sample_doc():
    return RawDoc(
        url=HttpUrl("https://example.com/article"),
        title="NVIDIA partners with TSMC",
        text="NVIDIA partners with TSMC to supply advanced chips. The companies collaborate closely.",
        published_at=datetime.utcnow(),
        source="test",
    )


def test_extraction_pipeline(sample_doc):
    extractors = [PatternRelationExtractor(), SimpleOpenIEExtractor()]
    pipeline = ExtractionPipeline(extractors)
    entities, edges, evidence = pipeline.extract(sample_doc)
    assert isinstance(entities, list)
    assert isinstance(edges, list)
    assert isinstance(evidence, list)

