"""M0 baseline fixtures for architecture migration testing.

This package provides shared fixtures for M1-M5 phases:
- plugin_manifests/     — valid and invalid Manifest fixtures for SDK tests
- workflows/            — YAML workflow fixtures for compilation and dry-run
- migrations/           — schema migration fixtures (old → new)
- source_snapshots/     — source version change fixtures for Evidence Ledger impact
- llm_recordings/       — recorded LLM responses for offline evaluation

Each subdirectory contains a ``.gitkeep`` so the directory structure survives
a clean Git checkout (Git does not track empty directories).

Fixture policy:
- Never write to real ``reports/``, ``data/chroma_db/``, or user project paths.
- Use temporary directories (pytest ``tmp_path``) or checked-in fixture files.
- Fixtures must be reproducible on any machine without real API keys.
- All LLM fixtures use cached/recorded responses or FakeModel.
"""

from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parent
