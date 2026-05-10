import sys
from unittest.mock import MagicMock

# MOCKING MISSING DEPENDENCIES BEFORE IMPORT
mock_langchain_core = MagicMock()
mock_langchain_core.prompts.ChatPromptTemplate = MagicMock()
mock_langchain_core.pydantic_v1.BaseModel = MagicMock
mock_langchain_core.pydantic_v1.Field = MagicMock
sys.modules["langchain_core"] = mock_langchain_core
sys.modules["langchain_core.prompts"] = mock_langchain_core.prompts
sys.modules["langchain_core.pydantic_v1"] = mock_langchain_core.pydantic_v1

mock_langchain_google = MagicMock()
mock_langchain_google.ChatGoogleGenerativeAI = MagicMock()
sys.modules["langchain_google_genai"] = mock_langchain_google

mock_langchain_openai = MagicMock()
mock_langchain_openai.ChatOpenAI = MagicMock()
sys.modules["langchain_openai"] = mock_langchain_openai

mock_google_genai = MagicMock()
# Mock the new client
mock_client = MagicMock()
mock_google_genai.Client.return_value = mock_client
# Mock generate_content response
mock_response = MagicMock()
mock_part = MagicMock()
mock_part.inline_data.data = b"fake_image_data"
mock_response.candidates[0].content.parts = [mock_part]
mock_client.models.generate_content.return_value = mock_response

sys.modules["google.genai"] = mock_google_genai
sys.modules["google.genai.types"] = MagicMock()

mock_old_genai = MagicMock()
sys.modules["google.generativeai"] = mock_old_genai

mock_neo4j = MagicMock()
sys.modules["neo4j"] = mock_neo4j

# Now we can import
import pytest
from unittest.mock import patch
from datetime import datetime

# We need to mock ingest.models.RawDoc and pydantic.HttpUrl because they might import things we have issues with?
# Actually pydantic should be there. 
# But extract.llm.structure_extractor imports the mocked libs.

from pipelines.agentic_pipeline import AgenticSearchPipeline
# We might need to reload if pytest already tried to import? No, separate process.

# Redefine simple mocks for data objects if real ones are hard to use
class MockRawDoc:
    def __init__(self, url, title, text, published_at, source):
        self.url = url
        self.title = title
        self.text = text
        self.published_at = published_at
        self.source = source

class MockEntity:
    def __init__(self, id, type, props=None):
        self.id = id
        self.type = type
        self.props = props or {}

class MockEdge:
    def __init__(self, src, dst, rel, props=None):
        self.src = src
        self.dst = dst
        self.rel = rel
        self.props = props or {}

class MockEvidence:
    def __init__(self, id, source, published_at, snippet, extractor, confidence=1.0):
        self.id = id
        self.source = source
        self.published_at = published_at
        self.snippet = snippet
        self.extractor = extractor
        self.confidence = confidence

@pytest.fixture
def mock_config():
    return {
        "search": {"tavily_api_key": "mock_key"},
        "extraction": {"model": "gemini-2.5-flash"},
        "visualization": {"prompt_model": "gemini-2.5-pro", "image_model": "gemini-3-pro-image"},
        "graph_store": {"neo4j": {}}
    }

@pytest.fixture
def mock_graph_store():
    store = MagicMock()
    return store

def test_agentic_pipeline_flow(mock_config, mock_graph_store):
    # Mock dependencies
    with patch("pipelines.agentic_pipeline.TavilyConnector") as MockConnector, \
         patch("pipelines.agentic_pipeline.LLMStructureExtractor") as MockExtractor, \
         patch("pipelines.agentic_pipeline.VisualizationService") as MockVizService, \
         patch("pipelines.agentic_pipeline.UpsertManager") as MockUpsertManager, \
         patch("pipelines.agentic_pipeline.PlanningService") as MockPlanningService, \
         patch("pipelines.agentic_pipeline.time.sleep") as MockSleep:

        # Setup Mocks
        connector_instance = MockConnector.return_value
        # Return 2 docs
        connector_instance.fetch.return_value = [
            MockRawDoc(
                url="http://news.com/1", title="News 1", text="Apple supplies Foxconn.", 
                published_at=datetime.utcnow(), source="tavily"
            ),
            MockRawDoc(
                url="http://news.com/2", title="News 2", text="TSMC delays chips.", 
                published_at=datetime.utcnow(), source="tavily"
            )
        ]

        extractor_instance = MockExtractor.return_value
        extractor_instance.name = "structured_llm"
        
        # We patch ExtractionPipeline
        with patch("pipelines.agentic_pipeline.ExtractionPipeline") as MockExtractionPipeline:
            pipeline_extractor = MockExtractionPipeline.return_value
            pipeline_extractor.extract.return_value = (
                [MockEntity(id="apple", type="Company", props={"name": "Apple"})],
                [MockEdge(src="apple", dst="foxconn", rel="SUPPLIES")],
                [MockEvidence(id="ev1", source="http://news.com/1", published_at=datetime.utcnow(), snippet="test", extractor="mock")]
            )
            
            # Planning Mock
            planning_instance = MockPlanningService.return_value
            planning_instance.generate_research_questions.return_value = ["Query 1", "Query 2"]

            # Visualization Mock
            viz_instance = MockVizService.return_value
            viz_instance.generate_infographic.return_value = "http://viz.com/image.png"
            
            # Initialize Pipeline
            pipeline = AgenticSearchPipeline(graph_store=mock_graph_store, config=mock_config)
            
            # Run Pipeline with Ticker
            stats = pipeline.run(ticker="TSLA", generate_visual=True)
            
            # Assertions
            assert stats["docs_found"] == 2 # Deduplication removes duplicates
            assert stats["visualization_url"] == "http://viz.com/image.png"
            assert stats["errors"] == []
            
            # Verify calls
            planning_instance.generate_research_questions.assert_called_once_with("TSLA")
            assert connector_instance.fetch.call_count == 2 # Called for each query
            assert pipeline_extractor.extract.call_count == 2 # 2 unique docs
            MockUpsertManager.return_value.upsert_with_provenance.assert_called_once()
            viz_instance.generate_infographic.assert_called_once()
            MockSleep.assert_called()
