import logging
from datetime import datetime
from typing import Any, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from extract.base import Extractor
from graph.models import Edge, Entity, Evidence
from ingest.models import RawDoc
from utils.config import get_llm_config

logger = logging.getLogger(__name__)


class SupplyChainRelation(BaseModel):
    """Represents a supply chain relationship between two entities."""
    source_entity: str = Field(..., description="Name of the source entity (e.g., Supplier)")
    source_type: str = Field(default="Company", description="Type of source entity (e.g., Company, Country)")
    target_entity: str | None = Field(default=None, description="Name of the target entity (e.g., Buyer)")
    target_type: str = Field(default="Company", description="Type of target entity (e.g., Company, Product)")
    relationship: str = Field(default="RELATED_TO", description="The nature of the relationship (e.g., supplies, delays, disrupts)")
    status: str = Field(default="active", description="Current status of the relationship (e.g., active, delayed, halted)")
    description: str = Field(default="", description="Brief explanation of the relationship context")


class ExtractionResult(BaseModel):
    relationships: List[SupplyChainRelation] = Field(default_factory=list)


class LLMStructureExtractor(Extractor):
    name = "structured_llm"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        llm_config = get_llm_config()
        
        model_name = self.config.get("model", llm_config.get("default_model", "gemini-2.5-flash"))
        temperature = self.config.get("temperature", 0.0)

        if "gemini" in model_name:
            api_key = llm_config.get("google_api_key")
            if not api_key:
                logger.warning("Google API key not found.")
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
            )
        elif "gpt" in model_name:
            api_key = llm_config.get("openai_api_key")
            if not api_key:
                logger.warning("OpenAI API key not found.")
            self.llm = ChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
            )
        else:
            raise ValueError(f"Unsupported model: {model_name}")

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert supply chain analyst. Extract supply chain relationships from the text. "
                       "Focus on supplier-buyer relationships, disruptions, and production updates."),
            ("user", "Text: {text}\n\nExtract structured relationships:"),
        ])

        self.chain = self.prompt | self.llm.with_structured_output(ExtractionResult)

    def extract(self, doc: RawDoc) -> tuple[list[Entity], list[Edge], list[Evidence]]:
        try:
            result: ExtractionResult = self.chain.invoke({"text": doc.text})
            
            entities: dict[str, Entity] = {}
            edges: list[Edge] = []
            evidence: list[Evidence] = []

            for rel in result.relationships:
                # Create Source Entity
                src_id = rel.source_entity.lower().replace(" ", "_")
                if src_id not in entities:
                    entities[src_id] = Entity(
                        id=src_id,
                        type=rel.source_type,
                        props={"name": rel.source_entity}
                    )

                # Skip if no target entity (self-referential events)
                if not rel.target_entity:
                    logger.debug(f"Skipping relationship without target: {rel.source_entity} -> {rel.relationship}")
                    continue

                # Create Target Entity
                tgt_id = rel.target_entity.lower().replace(" ", "_")
                if tgt_id not in entities:
                    entities[tgt_id] = Entity(
                        id=tgt_id,
                        type=rel.target_type,
                        props={"name": rel.target_entity}
                    )

                # Create Evidence
                ev_id = f"ev_{src_id}_{tgt_id}_{len(evidence)}"
                ev = Evidence(
                    id=ev_id,
                    source=doc.url,
                    published_at=doc.published_at or datetime.utcnow(),
                    snippet=rel.description or f"{rel.source_entity} {rel.relationship} {rel.target_entity}",
                    extractor="structured_llm",
                    confidence=0.9,
                )
                evidence.append(ev)

                # Create Edge
                edge = Edge(
                    src=src_id,
                    dst=tgt_id,
                    rel=rel.relationship.upper().replace(" ", "_"),
                    props={
                        "status": rel.status,
                        "description": rel.description,
                        "source_url": str(doc.url),
                        "date": doc.published_at.isoformat() if doc.published_at else None
                    },
                    evidence_ids=[ev_id]
                )
                edges.append(edge)

            return list(entities.values()), edges, evidence

        except Exception as e:
            logger.error(f"LLM extraction failed for doc {doc.url}: {e}")
            return [], [], []

