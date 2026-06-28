# Conflux

Conflux is an API-first multi-agent research system that combines local RAG, web search, and model knowledge into auditable Markdown and HTML research reports.

It is designed around the architecture in [docs/architecture.md](docs/architecture.md): three-source arbitration, Evidence Graph tracing, FactCheck, L4 deepening, SLO-aware run summaries, and repeatable acceptance checks.

## Highlights

- **API-first by default**: LLM and embedding calls use remote APIs. No local model is required.
- **Three-source research**: RAG, Web, and Model agents run as independent sources.
- **Explicit source status**: every source is marked `success`, `failed`, or `fallback`.
- **No fake evidence**: failed or fallback sources are excluded from consensus voting.
- **Evidence Graph**: key claims are represented as traceable evidence nodes with source metadata.
- **FactCheck gate**: checks whether important claims can be traced to valid sources.
- **Markdown + HTML delivery**: every completed research run can produce editable and browsable reports.
- **Acceptance verifier**: generated reports can be machine-checked before being treated as valid.

## Architecture

```text
User Query
   |
   v
Phase 2 Multi-Agent Graph
   |
   +-- RAG Agent   -> local Chroma retrieval
   +-- Web Agent   -> web search
   +-- Model Agent -> remote LLM world knowledge
   |
   v
Evidence Merge -> Arbitration -> Report Synthesis -> FactCheck -> L4 Deep Research
   |
   v
Markdown Report + HTML Report + Acceptance Check
```

The key rule is simple: only `success` sources can support factual claims. A failed web search or a model-written fallback is still shown to the user, but it cannot become evidence.

## Repository Layout

```text
.
├── config.yaml                  # API-first model, embedding, retrieval config
├── docs/architecture.md         # System design and phase roadmap
├── data/documents/              # Sample documents for RAG indexing
├── prompts/                     # Versioned agent, routing, evaluation prompts
├── src/conflux/
│   ├── __main__.py              # CLI entrypoint
│   ├── graph_v2.py              # Phase 2 multi-agent graph
│   ├── source_status.py         # success / failed / fallback payloads
│   ├── evidence.py              # Evidence Graph
│   ├── report.py                # Markdown and HTML report export
│   ├── acceptance.py            # Report acceptance verifier
│   ├── tools/                   # RAG, Web, Model tools
│   └── rag/                     # Chunking, indexing, hybrid retrieval
└── tests/                       # Unit and structural acceptance tests
```

## Requirements

- Python 3.11+
- Remote chat model API compatible with the configured provider
- Remote embedding API for RAG indexing

Install the project dependencies:

```powershell
python -m pip install -e .
```

For development:

```powershell
python -m pip install -e ".[dev]"
```

## Configuration

The default [config.yaml](config.yaml) uses an OpenAI-compatible API provider:

```yaml
models:
  reasoning:
    provider: openai_compatible
    model: deepseek-v4-flash
    base_url: https://www.dmxapi.cn/v1

embedding:
  provider: openai_compatible
  model: text-embedding-3-small
  base_url: https://www.dmxapi.cn/v1
```

Credentials must be provided through environment variables. Do not write keys into this repository.

Example:

```powershell
$env:OPENAI_API_KEY="your-api-key"
```

You can also override individual config values with `CONFLUX_` environment variables, for example:

```powershell
$env:CONFLUX_MODELS__REASONING__API_KEY="your-api-key"
$env:CONFLUX_EMBEDDING__API_KEY="your-api-key"
```

## Quick Start

Build the RAG index:

```powershell
$env:OPENAI_API_KEY="your-api-key"
python -m conflux --index data/documents
```

Run a Phase 2 research query:

```powershell
$env:OPENAI_API_KEY="your-api-key"
python -m conflux "研究 Multi-Agent RAG 中的三源仲裁，并说明 Evidence Graph、FactCheck、L4 深化研究在真实工程落地中的作用、风险和测试建议" --mode phase2 --output-dir reports
```

The CLI prints generated report paths:

```text
Markdown 报告：...\reports\YYYYMMDD-HHMMSS-....md
HTML 报告：...\reports\YYYYMMDD-HHMMSS-....html
```

## Validate A Generated Report

Use the built-in acceptance verifier:

```powershell
python -m conflux.acceptance path\to\report.md path\to\report.html
```

The verifier checks:

- Markdown and HTML both exist
- report contains final conclusions, source status, uncertainty, FactCheck, evidence summary, run summary, and quality score
- RAG/Web/Model all have explicit source status
- failed/fallback sources do not appear as evidence nodes
- Evidence Graph JSON is parseable
- FactCheck contains deterministic traceability checks
- quality score says the report is accepted

## Quality Gates

Before publishing changes:

```powershell
python -m pytest -q
python -m pip check
rg -n --hidden --glob '!data/chroma_db/**' --glob '!src/conflux.egg-info/**' --glob '!**/__pycache__/**' --glob '!reports*/**' -e 'sk-[A-Za-z0-9_-]{20,}' -e 'sk-proj-[A-Za-z0-9_-]{20,}' -e 'AKIA[0-9A-Z]{16}' -e 'AIza[0-9A-Za-z_-]{35}' .
```

## Current Phase Coverage

### Phase 1

- API-first model and embedding setup
- RAG indexing with remote embeddings
- Hybrid retrieval over Chroma
- Markdown and HTML report export
- Basic testing and dependency checks

### Phase 2

- RAG / Web / Model multi-agent execution
- Structured source status
- Evidence Graph
- Three-source arbitration prompt and deterministic safeguards
- FactCheck traceability checks
- L4 deep research supplement
- Run quality scoring
- Acceptance verifier for real report artifacts

## Security

- API keys belong in environment variables only.
- `.env`, generated reports, Chroma databases, caches, and runtime artifacts are ignored by Git.
- Failed tool calls are surfaced as `failed` and excluded from evidence consensus.
- Model-only补写 is marked as fallback/model knowledge instead of being treated as a retrieved source.

## License

No license has been selected yet. Add one before distributing this project publicly.
