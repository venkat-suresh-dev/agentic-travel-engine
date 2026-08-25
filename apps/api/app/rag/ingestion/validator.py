"""Corpus metadata validation."""

from __future__ import annotations

from app.rag.schemas import CorpusDocument


class CorpusValidationError(ValueError):
    """Raised when corpus metadata fails validation."""


def validate_document(document: CorpusDocument) -> CorpusDocument:
    if not document.id.strip():
        raise CorpusValidationError("document id is required")
    if not document.destination.strip():
        raise CorpusValidationError("destination is required")
    if not document.content.strip():
        raise CorpusValidationError("content is required")
    if not document.source_url.startswith(("http://", "https://")):
        raise CorpusValidationError("source_url must be an http(s) URL")
    return document
