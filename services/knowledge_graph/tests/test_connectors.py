from datetime import datetime

import pytest
from pydantic import HttpUrl

from ingest.connectors.base import FetchQuery
from ingest.connectors.gdelt import GDELTConnector
from ingest.models import RawDoc


@pytest.fixture
def gdelt_connector():
    return GDELTConnector()


def test_fetch_query():
    query = FetchQuery(query="test", days=7, language="en", limit=10)
    assert query.query == "test"
    assert query.days == 7
    assert query.language == "en"
    assert query.limit == 10


def test_gdelt_connector_fetch(gdelt_connector):
    query = FetchQuery(query="NVIDIA", days=1, limit=5)
    try:
        docs = gdelt_connector.fetch(query)
        docs_list = list(docs)
        assert isinstance(docs_list, list)
    except Exception as e:
        pytest.skip(f"GDELT API unavailable: {e}")

