"""Semantic-ish chunking for curated destination documents."""

from __future__ import annotations

import re

import tiktoken

from app.rag.schemas import CorpusChunk, CorpusDocument, RagTopic

DEFAULT_TARGET_TOKENS = 400
DEFAULT_ENCODING = "cl100k_base"


def chunk_document(
    document: CorpusDocument,
    *,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    encoding_name: str = DEFAULT_ENCODING,
) -> list[CorpusChunk]:
    """Split a document into paragraph-aware chunks near the target token size."""
    encoding = tiktoken.get_encoding(encoding_name)
    paragraphs = _split_paragraphs(document.content)
    if not paragraphs:
        return []

    chunks: list[CorpusChunk] = []
    current_parts: list[str] = []
    current_tokens = 0
    chunk_index = 0

    def flush_chunk() -> None:
        nonlocal chunk_index, current_parts, current_tokens
        if not current_parts:
            return
        content = "\n\n".join(current_parts).strip()
        chunks.append(
            _build_chunk(
                document=document,
                chunk_index=chunk_index,
                content=content,
            )
        )
        chunk_index += 1
        current_parts = []
        current_tokens = 0

    for paragraph in paragraphs:
        paragraph_tokens = len(encoding.encode(paragraph))
        if paragraph_tokens > target_tokens:
            flush_chunk()
            for sentence_chunk in _split_long_paragraph(
                paragraph, encoding, target_tokens
            ):
                chunks.append(
                    _build_chunk(
                        document=document,
                        chunk_index=chunk_index,
                        content=sentence_chunk,
                    )
                )
                chunk_index += 1
            continue

        if current_tokens + paragraph_tokens > target_tokens and current_parts:
            flush_chunk()

        current_parts.append(paragraph)
        current_tokens += paragraph_tokens

    flush_chunk()
    return chunks


def build_chunk_id(document_id: str, document_version: str, chunk_index: int) -> str:
    return f"{document_id}-{document_version}-{chunk_index:02d}"


def build_search_text(document: CorpusDocument, content: str) -> str:
    return (
        f"{document.destination} {document.topic.value} {document.title}\n{content}"
    ).strip()


def _build_chunk(
    *,
    document: CorpusDocument,
    chunk_index: int,
    content: str,
) -> CorpusChunk:
    return CorpusChunk(
        chunk_id=build_chunk_id(document.id, document.version, chunk_index),
        document_id=document.id,
        destination=document.destination,
        topic=RagTopic(document.topic),
        content=content,
        source_url=document.source_url,
        source_name=document.source_name,
        document_version=document.version,
        last_verified=document.last_verified,
        chunk_index=chunk_index,
        search_text=build_search_text(document, content),
    )


def _split_paragraphs(content: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    return parts


def _split_long_paragraph(
    paragraph: str,
    encoding: tiktoken.Encoding,
    target_tokens: int,
) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        sentence_tokens = len(encoding.encode(sentence))
        if current_tokens + sentence_tokens > target_tokens and current_parts:
            chunks.append(" ".join(current_parts).strip())
            current_parts = []
            current_tokens = 0
        current_parts.append(sentence)
        current_tokens += sentence_tokens

    if current_parts:
        chunks.append(" ".join(current_parts).strip())
    return chunks
