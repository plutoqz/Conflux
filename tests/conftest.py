"""Shared pytest fixtures.

FakeEmbedding is injected into the P2 radar module so the embedding coarse
rank runs deterministically offline; real API calls are only made by explicit
CLI runs, never by the test-suite.
"""

from __future__ import annotations

import hashlib

import pytest


_TERM_DIMS = (
    ("gis", 0), ("geospatial", 0), ("spatial", 0),
    ("agent", 1), ("tool", 1),
    ("knowledge graph", 2), ("geokg", 2), ("graph", 2),
    ("verif", 3), ("audit", 3), ("reproduc", 3), ("evaluat", 3),
)


class FakeEmbedding:
    """Deterministic keyword-grounded embedding for offline tests."""

    def __init__(self, dim: int = 8) -> None:
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        lowered = str(text or "").casefold()
        vector = [0.0] * self.dim
        for term, dimension in _TERM_DIMS:
            if term in lowered:
                vector[dimension] = 1.0
        digest = hashlib.sha256(str(text or "").encode("utf-8")).digest()
        for index in range(4, self.dim):
            vector[index] = (digest[index % len(digest)] % 10) / 10.0
        return vector

    def embed_documents(self, texts) -> list[list[float]]:
        return [self._vec(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


@pytest.fixture(autouse=True)
def _fake_p2_embedding(monkeypatch):
    """Make the P2 radar use FakeEmbedding for all offline tests."""
    monkeypatch.setattr(
        "conflux.paper_radar.radar.create_embedding_model",
        lambda: FakeEmbedding(),
    )
