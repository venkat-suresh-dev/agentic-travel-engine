"""Typed contracts for the destination knowledge RAG subsystem."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RagTopic(StrEnum):
    NEIGHBORHOODS = "neighborhoods"
    TRANSPORT = "transport"
    VISA_ENTRY = "visa_entry"
    CULTURE = "culture"
    ETIQUETTE = "etiquette"
    SAFETY = "safety"
    MONEY = "money"
    LOCAL_CUSTOMS = "local_customs"
    TRIP_PLANNING = "trip_planning"


class RetrievalMethod(StrEnum):
    VECTOR = "vector"
    LEXICAL = "lexical"
    HYBRID = "hybrid"


class CorpusDocument(BaseModel):
    """Versioned curated destination knowledge document."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    country: str = Field(min_length=1)
    topic: RagTopic
    title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    content: str = Field(min_length=1)
    last_verified: date
    version: str = Field(min_length=1)


class CorpusChunk(BaseModel):
    """Normalized chunk produced during ingestion."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    destination: str
    topic: RagTopic
    content: str
    source_url: str
    source_name: str
    document_version: str
    last_verified: date
    chunk_index: int = Field(ge=0)
    search_text: str


class RetrievalRequest(BaseModel):
    """Application retrieval request contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    topics: list[RagTopic] | None = None


class RetrievedChunk(BaseModel):
    """Single retrieved knowledge chunk with provenance."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    content: str
    score: float
    retrieval_method: RetrievalMethod
    destination: str
    topic: RagTopic
    source_url: str
    source_name: str
    document_version: str
    last_verified: date
    document_id: str
    chunk_index: int


class RetrievedContext(BaseModel):
    """Ranked retrieval result set for downstream consumers."""

    model_config = ConfigDict(extra="forbid")

    query: str
    destination: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    retrieved_at: datetime
    is_reference_data_only: bool = True


class IngestionReport(BaseModel):
    """Summary of a corpus ingestion run."""

    model_config = ConfigDict(extra="forbid")

    documents_processed: int
    chunks_written: int
    chunks_removed: int
    corpus_version: str
