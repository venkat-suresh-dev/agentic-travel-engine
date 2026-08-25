"""Hybrid retrieval scoring and merge logic."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.schemas import RagTopic, RetrievalMethod, RetrievedChunk

VECTOR_WEIGHT = 0.6
LEXICAL_WEIGHT = 0.4


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    chunk: RetrievedChunk
    vector_score: float = 0.0
    lexical_score: float = 0.0

    @property
    def hybrid_score(self) -> float:
        return (VECTOR_WEIGHT * self.vector_score) + (
            LEXICAL_WEIGHT * self.lexical_score
        )


def merge_ranked_results(
    *,
    vector_results: list[RetrievedChunk],
    lexical_results: list[RetrievedChunk],
    top_k: int,
) -> list[RetrievedChunk]:
    candidates: dict[str, RankedCandidate] = {}

    for result in vector_results:
        candidates[result.chunk_id] = RankedCandidate(
            chunk=result.model_copy(
                update={"retrieval_method": RetrievalMethod.VECTOR}
            ),
            vector_score=result.score,
        )

    for result in lexical_results:
        existing = candidates.get(result.chunk_id)
        if existing is None:
            candidates[result.chunk_id] = RankedCandidate(
                chunk=result.model_copy(
                    update={"retrieval_method": RetrievalMethod.LEXICAL}
                ),
                lexical_score=result.score,
            )
            continue
        candidates[result.chunk_id] = RankedCandidate(
            chunk=existing.chunk.model_copy(
                update={"retrieval_method": RetrievalMethod.HYBRID}
            ),
            vector_score=existing.vector_score,
            lexical_score=max(existing.lexical_score, result.score),
        )

    ranked = sorted(
        candidates.values(),
        key=lambda candidate: (
            -candidate.hybrid_score,
            -candidate.vector_score,
            -candidate.lexical_score,
            candidate.chunk.chunk_index,
        ),
    )

    merged: list[RetrievedChunk] = []
    for candidate in ranked[:top_k]:
        merged.append(
            candidate.chunk.model_copy(
                update={
                    "score": round(candidate.hybrid_score, 6),
                    "retrieval_method": (
                        RetrievalMethod.HYBRID
                        if candidate.vector_score > 0 and candidate.lexical_score > 0
                        else candidate.chunk.retrieval_method
                    ),
                }
            )
        )
    return merged


def normalize_destination(destination: str) -> str:
    return destination.strip().casefold()


def topic_values(topics: list[RagTopic] | None) -> list[str] | None:
    if topics is None:
        return None
    return [topic.value for topic in topics]
