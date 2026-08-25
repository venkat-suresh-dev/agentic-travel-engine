"""Corpus loading utilities."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.rag.schemas import CorpusDocument

DEFAULT_CORPUS_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "rag"
    / "corpus"
    / "dubai"
    / "corpus.json"
)


class CorpusManifest(BaseModel):
    corpus_version: str = Field(min_length=1)
    documents: list[CorpusDocument]


def load_corpus_manifest(path: Path | None = None) -> CorpusManifest:
    corpus_path = path or DEFAULT_CORPUS_PATH
    raw = json.loads(corpus_path.read_text(encoding="utf-8"))
    return CorpusManifest.model_validate(raw)


def load_corpus_documents(path: Path | None = None) -> tuple[str, list[CorpusDocument]]:
    manifest = load_corpus_manifest(path)
    return manifest.corpus_version, manifest.documents
