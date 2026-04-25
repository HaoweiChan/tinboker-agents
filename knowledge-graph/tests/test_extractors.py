from datetime import datetime

import pytest
from pydantic import HttpUrl

from extract.openie.minie import SimpleOpenIEExtractor
from extract.rules.patterns import PatternRelationExtractor
from extract.rules.spacy_ner import SpacyNERExtractor
from ingest.models import RawDoc


@pytest.fixture
def sample_doc():
    return RawDoc(
        url=HttpUrl("https://example.com/article"),
        title="NVIDIA supplies chips to TSMC",
        text="NVIDIA supplies advanced chips to TSMC. The companies have a strong partnership.",
        published_at=datetime.utcnow(),
        source="test",
    )


def test_spacy_ner_extractor(sample_doc):
    try:
        extractor = SpacyNERExtractor()
        entities, edges, evidence = extractor.extract(sample_doc)
        assert isinstance(entities, list)
        assert isinstance(edges, list)
        assert isinstance(evidence, list)
    except ImportError:
        pytest.skip("spacy not installed")


def test_pattern_relation_extractor(sample_doc):
    extractor = PatternRelationExtractor()
    entities, edges, evidence = extractor.extract(sample_doc)
    assert isinstance(entities, list)
    assert isinstance(edges, list)
    assert isinstance(evidence, list)
    assert len(edges) > 0


def test_simple_openie_extractor(sample_doc):
    extractor = SimpleOpenIEExtractor()
    entities, edges, evidence = extractor.extract(sample_doc)
    assert isinstance(entities, list)
    assert isinstance(edges, list)
    assert isinstance(evidence, list)

