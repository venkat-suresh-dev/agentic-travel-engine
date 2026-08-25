"""Formatting package."""

from app.rag.formatting.context import (
    REFERENCE_DATA_HEADER,
    REFERENCE_DATA_PREAMBLE,
    format_retrieved_chunk,
    format_retrieved_context,
)

__all__ = [
    "REFERENCE_DATA_HEADER",
    "REFERENCE_DATA_PREAMBLE",
    "format_retrieved_chunk",
    "format_retrieved_context",
]
