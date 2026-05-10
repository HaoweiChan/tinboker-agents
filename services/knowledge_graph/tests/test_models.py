from datetime import datetime

import pytest
from pydantic import HttpUrl

from graph.models import Edge, Entity, Evidence


def test_entity():
    entity = Entity(id="person:john_doe", type="Person", props={"name": "John Doe"})
    assert entity.id == "person:john_doe"
    assert entity.type == "Person"


def test_edge():
    edge = Edge(src="org:nvidia", dst="org:tsmc", rel="SUPPLIES")
    assert edge.src == "org:nvidia"
    assert edge.dst == "org:tsmc"
    assert edge.rel == "SUPPLIES"


def test_evidence():
    evidence = Evidence(
        id="evidence:123",
        source=HttpUrl("https://example.com"),
        published_at=datetime.utcnow(),
        snippet="NVIDIA supplies chips",
        extractor="test",
        confidence=0.8,
    )
    assert evidence.id == "evidence:123"
    assert evidence.confidence == 0.8

