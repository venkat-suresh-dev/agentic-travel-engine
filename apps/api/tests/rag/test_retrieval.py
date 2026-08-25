"""RAG retrieval tests."""

from __future__ import annotations

from datetime import date

from app.rag.embeddings.fake import FakeEmbeddingProvider
from app.rag.ingestion.pipeline import RagIngestionPipeline
from app.rag.retrieval.lexical import LexicalRetriever
from app.rag.retrieval.merger import merge_ranked_results
from app.rag.retrieval.vector import VectorRetriever
from app.rag.schemas import RagTopic, RetrievalMethod, RetrievalRequest, RetrievedChunk
from app.rag.service import RAGRetriever
from sqlalchemy.ext.asyncio import AsyncSession
from tests.rag.conftest import sample_document


async def test_vector_retrieval_returns_relevant_dubai_chunk(
    rag_retriever: RAGRetriever,
) -> None:
    context = await rag_retriever.retrieve(
        RetrievalRequest(
            query="Dubai metro and public transport",
            destination="Dubai",
            top_k=3,
            topics=[RagTopic.TRANSPORT],
        )
    )
    assert context.chunks
    assert all(chunk.destination == "Dubai" for chunk in context.chunks)
    assert any(chunk.topic == RagTopic.TRANSPORT for chunk in context.chunks)


async def test_destination_filtering_excludes_other_destinations(
    db_session: AsyncSession,
    fake_embedding_provider: FakeEmbeddingProvider,
) -> None:
    pipeline = RagIngestionPipeline(
        session=db_session,
        embedding_provider=fake_embedding_provider,
    )
    await pipeline._ingest_document(sample_document(destination="Tokyo"), "v-test")
    await pipeline._ingest_document(
        sample_document(document_id="dubai-filter-doc", destination="Dubai"),
        "v-test",
    )
    await db_session.commit()

    retriever = VectorRetriever(db_session)
    vector = await retriever.retrieve(
        query_embedding=await fake_embedding_provider.embed_query("transport"),
        destination="Dubai",
        top_k=5,
    )
    assert vector
    assert all(chunk.destination == "Dubai" for chunk in vector)


async def test_topic_filtering(rag_retriever: RAGRetriever) -> None:
    context = await rag_retriever.retrieve(
        RetrievalRequest(
            query="payment cards and cash",
            destination="Dubai",
            top_k=5,
            topics=[RagTopic.MONEY],
        )
    )
    assert context.chunks
    assert all(chunk.topic == RagTopic.MONEY for chunk in context.chunks)


async def test_top_k_limits_results(rag_retriever: RAGRetriever) -> None:
    context = await rag_retriever.retrieve(
        RetrievalRequest(query="Dubai planning", destination="Dubai", top_k=2)
    )
    assert len(context.chunks) <= 2


async def test_lexical_keyword_match(
    ingested_rag_corpus: tuple[AsyncSession, FakeEmbeddingProvider],
) -> None:
    session, _provider = ingested_rag_corpus
    lexical = LexicalRetriever(session)
    results = await lexical.retrieve(
        query="Nol card metro",
        destination="Dubai",
        top_k=3,
    )
    assert results
    assert any("metro" in result.content.lower() for result in results)


async def test_hybrid_merge_removes_duplicate_chunks() -> None:
    shared = RetrievedChunk(
        chunk_id="shared",
        content="shared content",
        score=0.8,
        retrieval_method=RetrievalMethod.VECTOR,
        destination="Dubai",
        topic=RagTopic.TRANSPORT,
        source_url="https://example.com",
        source_name="Example",
        document_version="v1",
        last_verified=date(2026, 1, 1),
        document_id="doc",
        chunk_index=0,
    )
    lexical = shared.model_copy(
        update={"score": 0.5, "retrieval_method": RetrievalMethod.LEXICAL}
    )
    merged = merge_ranked_results(
        vector_results=[shared],
        lexical_results=[lexical],
        top_k=5,
    )
    assert len(merged) == 1
    assert merged[0].retrieval_method == RetrievalMethod.HYBRID


async def test_hybrid_deterministic_ranking() -> None:
    vector = [
        RetrievedChunk(
            chunk_id="a",
            content="a",
            score=0.9,
            retrieval_method=RetrievalMethod.VECTOR,
            destination="Dubai",
            topic=RagTopic.TRANSPORT,
            source_url="https://example.com/a",
            source_name="A",
            document_version="v1",
            last_verified=date(2026, 1, 1),
            document_id="a-doc",
            chunk_index=0,
        )
    ]
    lexical = [
        RetrievedChunk(
            chunk_id="b",
            content="b",
            score=0.7,
            retrieval_method=RetrievalMethod.LEXICAL,
            destination="Dubai",
            topic=RagTopic.SAFETY,
            source_url="https://example.com/b",
            source_name="B",
            document_version="v1",
            last_verified=date(2026, 1, 1),
            document_id="b-doc",
            chunk_index=0,
        )
    ]
    first = merge_ranked_results(
        vector_results=vector, lexical_results=lexical, top_k=2
    )
    second = merge_ranked_results(
        vector_results=vector, lexical_results=lexical, top_k=2
    )
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


async def test_provenance_metadata_survives_retrieval(
    rag_retriever: RAGRetriever,
) -> None:
    context = await rag_retriever.retrieve(
        RetrievalRequest(query="Dubai neighborhoods", destination="Dubai", top_k=1)
    )
    chunk = context.chunks[0]
    assert chunk.source_url.startswith("https://")
    assert chunk.source_name
    assert chunk.document_version
    assert chunk.last_verified
    assert chunk.chunk_id


async def test_freshness_metadata_is_preserved(rag_retriever: RAGRetriever) -> None:
    context = await rag_retriever.retrieve(
        RetrievalRequest(
            query="visa entry requirements overview", destination="Dubai", top_k=3
        )
    )
    assert context.chunks
    assert all(chunk.last_verified >= date(2026, 1, 1) for chunk in context.chunks)
    assert all(chunk.document_version for chunk in context.chunks)
