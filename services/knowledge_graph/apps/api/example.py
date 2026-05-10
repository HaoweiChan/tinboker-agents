"""
Example API endpoints using the same service layer as CLI and MCP servers.

This demonstrates how FastAPI/Flask endpoints would use the same services.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.extraction_service import ExtractionService
from services.graph_service import GraphService
from services.ingestion_service import IngestionService

app = FastAPI()


class IngestRequest(BaseModel):
    source: str = "gdelt"
    query: str
    days: int = 7


class QueryRequest(BaseModel):
    cypher: str


@app.post("/api/v1/ingest")
async def ingest_endpoint(request: IngestRequest):
    service = IngestionService()
    try:
        docs = service.ingest(
            source=request.source,
            query=request.query,
            days=request.days,
        )
        return {"status": "success", "count": len(docs), "docs": [doc.model_dump() for doc in docs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/extract")
async def extract_endpoint(docs: list[dict], pipeline: str = "rules+openie"):
    service = ExtractionService()
    from ingest.models import RawDoc

    raw_docs = [RawDoc(**doc) for doc in docs]
    entities, edges, evidence = service.extract(raw_docs, pipeline=pipeline)

    return {
        "entities": [e.model_dump() for e in entities],
        "edges": [e.model_dump() for e in edges],
        "evidence": [e.model_dump() for e in evidence],
    }


@app.post("/api/v1/query")
async def query_endpoint(request: QueryRequest):
    service = GraphService()
    try:
        results = service.query(request.cypher)
        return {"results": results}
    finally:
        service.close()


@app.get("/api/v1/neighbors/{entity_id}")
async def get_neighbors(entity_id: str, hop: int = 2):
    service = GraphService()
    try:
        results = service.get_neighbors(entity_id, hop=hop)
        return {"neighbors": results}
    finally:
        service.close()


@app.get("/api/v1/explain-edge")
async def explain_edge(src_id: str, rel: str, dst_id: str):
    service = GraphService()
    try:
        results = service.explain_edge(src_id, rel, dst_id)
        return {"evidence": results}
    finally:
        service.close()

