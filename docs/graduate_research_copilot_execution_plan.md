# Graduate Research Copilot Execution Plan

> Purpose: turn the product spec into an implementation checklist with priority, concrete deliverables, and acceptance standards.  
> Scope: first productized version for CS, AI, GIS, and engineering graduate students.  
> Related spec: `docs/graduate_research_copilot_product_spec.md`

## 1. Priority Rules

Use these priorities when deciding what to implement next.

| Priority | Meaning | Ship Rule |
|---|---|---|
| P0 | Required for the first usable MVP. Without it, the product story is incomplete. | Must be finished before calling the project Graduate Research Copilot MVP. |
| P1 | Strong differentiator or quality requirement. It makes the MVP trustworthy and demo-ready. | Should be finished before resume/demo polishing. |
| P2 | Important extension after the core loops work. | Implement only after P0 and most P1 items are stable. |
| P3 | Nice-to-have or future product layer. | Defer unless it directly supports a demo or user test. |

Hard constraints:

- Default runs must work without real API keys.
- Real network/API runs must be opt-in.
- Large PDFs, Chroma stores, reports, logs, and local secrets must not enter Git.
- Every new feature needs at least one deterministic test or fixture.
- Every user-facing report must preserve evidence provenance.

## 2. Global Definition Of Done

An item is complete only when all applicable checks pass.

- `python -m pytest -q` passes.
- New CLI commands have `--help` text or README/docs examples.
- New data contracts have unit tests.
- New generated artifacts are either ignored or intentionally committed as small examples.
- Any new real API path has an offline fake path.
- Reports include source status, evidence references, uncertainty, or explicit "not available" notes.
- No real secrets are present in staged files.

## 3. MVP Cut Line

The MVP is not a general AI companion. The MVP ends at these four loops:

- Research Profile
- Paper Radar
- Evidence RAG
- Progress Audit

Deferred from MVP:

- full web UI;
- multi-user SaaS;
- Zotero sync;
- automatic paper writing;
- full PDF figure/table understanding;
- complex persistent knowledge graph;
- therapist-style mental-health assistant.

## 4. Workstream Overview

| ID | Priority | Workstream | Outcome |
|---|---|---|---|
| R0 | P0 | Planning and repo hygiene | Clear docs, ignored artifacts, stable current baseline. |
| R1 | P0 | Research Profile | User research context can be loaded, validated, and reused. |
| R2 | P0 | Paper Ingestion Core | Papers can be loaded/crawled into stable records. |
| R3 | P0 | Paper Radar and Inbox | Papers are scored, filtered, analyzed, and reported. |
| R4 | P0 | RAG Promotion | High-value papers enter the knowledge base with citations. |
| R4.5 | P1 | Local Research Workbench | Local UI for paper inbox, promotion review, reports, and API/model testing. |
| R5 | P1 | Evidence Q&A Integration | Q&A distinguishes local papers, web, and model inference. |
| R6 | P0 | Progress Audit MVP | Local projects can be audited using evidence from files and Git. |
| R7 | P1 | Weekly Research Report | Literature and progress are summarized together. |
| R8 | P2 | Trust and Evaluation Expansion | Better eval, prompt-injection fixtures, cost/run ledgers. |
| R9 | P3 | UI and Product Polish | Optional TUI/Web UI and richer user experience. |

## 5. R0: Planning And Repo Hygiene

Priority: P0  
Goal: keep the project easy to run, review, and extend before adding product modules.

### Functions To Implement

- Keep product spec and execution plan under `docs/`.
- Keep local corpus artifacts out of Git.
- Ensure CI covers offline tests and eval scripts.
- Keep example reports small and deterministic.

### Target Files

- `.gitignore`
- `.github/workflows/ci.yml`
- `README.md`
- `docs/graduate_research_copilot_product_spec.md`
- `docs/graduate_research_copilot_execution_plan.md`

### Acceptance Criteria

- `data/documents/papers/`, `data/chroma_db/`, `reports/`, `.env`, and generated logs are ignored.
- CI runs install, unit tests, import checks, secret scan, retrieval eval, and report eval.
- README clearly explains current Conflux capabilities and the new Graduate Research Copilot direction.
- The repo can be cloned and tested without API keys.

### Verification

- Run `python -m pytest -q`.
- Run `python scripts/eval_retrieval.py --offline --out-dir reports/eval`.
- Run `python scripts/eval_reports.py --offline --out-dir reports/eval`.
- Confirm `git status --short` does not show generated artifacts after verification.

## 6. R1: Research Profile

Priority: P0  
Goal: make the user's research context a first-class, validated object.

### Functions To Implement

- Define `ResearchProfile`.
- Load profile from YAML.
- Validate required fields and useful constraints.
- Convert one AcademyHunter-style profile into the Conflux profile format.
- Expose profile path through CLI.

### Proposed CLI

```powershell
python -m conflux.profile validate profiles/example_gis_agent.yaml
python -m conflux.profile show profiles/example_gis_agent.yaml
```

### Target Files

```text
src/conflux/research_profile/
  __init__.py
  models.py
  loader.py
  validators.py

profiles/
  example_gis_agent.yaml

tests/
  test_research_profile.py
```

### Data Contract

Required fields:

- `id`
- `name`
- `fields`
- `research_questions`
- `keywords`

Optional but recommended fields:

- `negative_keywords`
- `target_venues`
- `tracked_scholars`
- `project_paths`
- `document_paths`
- `paper_sources`
- `report_cadence`

### Acceptance Criteria

- Valid profile loads into a typed object.
- Missing required fields produce a clear error.
- Empty keyword and research question lists are rejected.
- Path fields are normalized but nonexistent paths only warn by default.
- The example profile covers CS/AI/GIS graduate research.

### Tests

- `test_load_valid_profile`
- `test_missing_required_field_fails`
- `test_empty_research_questions_fail`
- `test_academy_hunter_profile_can_be_mapped`

### Non-Goals

- Profile editor UI.
- Multi-user profile management.

## 7. R2: Paper Ingestion Core

Priority: P0  
Goal: create stable paper records from offline fixtures and arXiv.

### Functions To Implement

- Define `PaperRecord`, `PaperAnalysis`, and `IngestionDecision`.
- Add offline fixture loader for deterministic tests.
- Port or wrap AcademyHunter's arXiv query builder and crawler.
- Normalize arXiv records into `PaperRecord`.
- Deduplicate by arXiv ID, DOI, title hash, and title+abstract similarity.
- Add negative keyword filtering based on profile.

### Proposed CLI

```powershell
python -m conflux.papers load-fixture tests/fixtures/papers/arxiv_sample.json
python -m conflux.papers crawl --profile profiles/example_gis_agent.yaml --source arxiv --dry-run
```

### Target Files

```text
src/conflux/paper_ingestion/
  __init__.py
  models.py
  fixtures.py
  arxiv_source.py
  dedup.py
  filters.py

tests/fixtures/papers/
  arxiv_sample.json

tests/
  test_paper_ingestion.py
```

### Acceptance Criteria

- Offline fixture produces deterministic `PaperRecord` objects.
- arXiv crawler is isolated behind an interface and not required for tests.
- Duplicate papers collapse into one record with merged metadata.
- Negative filters remove clearly off-topic papers.
- Failed network crawl returns a structured failure result instead of crashing.

### Tests

- `test_fixture_loader_returns_paper_records`
- `test_arxiv_record_normalization`
- `test_dedup_by_id_and_title`
- `test_negative_filter_removes_off_topic_paper`
- `test_crawler_failure_is_structured`

### Non-Goals

- Semantic Scholar integration.
- DBLP integration.
- PDF download.

## 8. R3: Paper Radar And Inbox

Priority: P0  
Goal: turn raw papers into a useful reading inbox.

### Functions To Implement

- Compute deterministic L1 relevance score using profile keywords and optional embeddings.
- Add optional L2 LLM relevance scoring behind `--real` or configured API key.
- Generate `PaperAnalysis` with reading level: `deep`, `skim`, `skip`.
- Produce a Markdown paper inbox report.
- Persist a small JSON summary for downstream indexing.

### Proposed CLI

```powershell
python -m conflux.papers inbox --profile profiles/example_gis_agent.yaml --fixture tests/fixtures/papers/arxiv_sample.json --out-dir reports/papers
python -m conflux.papers inbox --profile profiles/example_gis_agent.yaml --source arxiv --real --out-dir reports/papers
```

### Target Files

```text
src/conflux/paper_ingestion/
  scorer.py
  analyzer.py
  inbox_report.py
  pipeline.py

tests/
  test_paper_radar.py
```

### Acceptance Criteria

- Offline inbox command runs without API keys.
- Each paper has relevance score, matched profile terms, reading level, and reason.
- `deep` papers have enough metadata for later ingestion.
- Markdown report lists top papers, skipped papers, and reasons.
- JSON output can be consumed by RAG promotion.

### Tests

- `test_keyword_relevance_scoring_is_deterministic`
- `test_reading_level_thresholds`
- `test_inbox_report_contains_scores_and_reasons`
- `test_offline_inbox_pipeline_writes_json_and_markdown`

### Non-Goals

- Perfect ranking quality.
- Full paper understanding from PDF.

## 9. R4: RAG Promotion

Priority: P0  
Goal: promote selected papers into the Conflux knowledge base without polluting it.

### Functions To Implement

- Implement `IngestionDecision` policy.
- Convert paper summaries and abstracts to `Document` objects.
- Add paper-aware metadata to chunks.
- Support `summary_only`, `full_text`, `metadata_only`, `pinned`, and `skip`.
- Ensure RAG evidence refs identify paper ID and chunk ID.
- Add retrieval eval cases for paper corpus.

### Proposed CLI

```powershell
python -m conflux.papers promote reports/papers/inbox.json --policy default --index
python -m conflux --index data/documents
```

### Target Files

```text
src/conflux/paper_ingestion/
  ingestion_policy.py

src/conflux/knowledge/
  __init__.py
  source_models.py
  paper_indexer.py
  citation_resolver.py

src/conflux/rag/
  chunker.py
  indexer.py

data/documents/rag-eval-test-cases.json
```

### Acceptance Criteria

- `skip` papers are not indexed.
- `metadata_only` papers are searchable only as metadata, not factual content.
- `summary_only` papers index title, abstract, and analysis summary.
- `full_text` papers include PDF-derived chunks only when text extraction succeeds.
- RAG citations expose paper ID, source type, and chunk ID.
- Retrieval eval includes at least five paper-specific cases.

### Tests

- `test_ingestion_policy_thresholds`
- `test_summary_only_paper_becomes_document`
- `test_skip_paper_not_indexed`
- `test_paper_citation_round_trip`
- `test_retrieval_eval_includes_paper_cases`

### Non-Goals

- Large-scale PDF corpus management.
- Full-text OCR.

## 10. R5: Evidence Q&A Integration

Priority: P1  
Goal: make Q&A explicitly distinguish local papers, web evidence, and model inference.

### Functions To Implement

- Extend `SourceResult` metadata with knowledge source type.
- Add paper citation appendix to generated reports.
- Make synthesizer language distinguish:
  - `LocalPaper`;
  - `LocalNote`;
  - `ProjectDoc`;
  - `Web`;
  - `ModelInference`.
- Ensure FactCheck treats model inference as non-external evidence.
- Add source coverage summary to run summary JSON.

### Target Files

```text
src/conflux/source_status.py
src/conflux/evidence.py
src/conflux/report.py
src/conflux/graph_v2.py
src/conflux/tools/rag.py
tests/test_paper_evidence_qa.py
```

### Acceptance Criteria

- Final reports do not collapse all local RAG results into a generic `[RAG]` label.
- Local paper claims include paper citation refs.
- Model-only claims are labeled as inference or low-certainty reasoning.
- Failed/fallback sources are not counted as evidence.
- Report appendix lists paper source metadata.

### Tests

- `test_local_paper_source_type_appears_in_report`
- `test_model_inference_not_external_evidence`
- `test_failed_source_excluded_from_paper_evidence_graph`
- `test_report_appendix_lists_paper_citations`

### Non-Goals

- UI citation browser.

## 11. R6: Progress Audit MVP

Priority: P0  
Goal: audit real research progress from local project evidence.

### Functions To Implement

- Define `ProjectSnapshot` and `ProgressAuditReport`.
- Inspect local Git branch, HEAD, dirty files, and recent commits.
- Inspect result artifact directories for new or changed files.
- Inspect test status using configured commands.
- Inspect report files for modified sections and claims.
- Compare current snapshot to previous snapshot.
- Generate progress audit Markdown and JSON.

### Proposed CLI

```powershell
python -m conflux.progress snapshot --profile profiles/example_gis_agent.yaml --out-dir reports/progress
python -m conflux.progress audit --profile profiles/example_gis_agent.yaml --since last --out-dir reports/progress
```

### Target Files

```text
src/conflux/progress_audit/
  __init__.py
  models.py
  git_inspector.py
  artifact_inspector.py
  test_inspector.py
  report_inspector.py
  auditor.py
  progress_report.py

tests/fixtures/progress_repo/
tests/test_progress_audit.py
```

### Acceptance Criteria

- Snapshot can be generated for at least one local Git project.
- Audit report separates:
  - real progress;
  - weak signals;
  - risks;
  - recommended next actions.
- Every real progress claim has evidence refs.
- Dirty worktree and failing tests are surfaced as risks.
- New result files are detected and summarized.
- Missing baseline produces a clear first-run message.

### Tests

- `test_git_snapshot_reads_branch_and_head`
- `test_dirty_files_are_reported`
- `test_new_artifact_detected_since_baseline`
- `test_failing_test_command_becomes_risk`
- `test_progress_report_requires_evidence_refs`
- `test_first_run_without_baseline_is_graceful`

### Non-Goals

- Remote GitHub issue sync.
- Automatic interpretation of arbitrary binary result formats.
- Running destructive or long experiment commands.

## 12. R7: Weekly Research Report

Priority: P1  
Goal: combine literature updates and progress audit into one report useful for weekly self-review or advisor meetings.

### Functions To Implement

- Combine paper inbox summary and progress audit.
- Show what changed since last report.
- List top papers to read, top project risks, and next actions.
- Include source and artifact evidence refs.
- Export Markdown and HTML.

### Proposed CLI

```powershell
python -m conflux.weekly --profile profiles/example_gis_agent.yaml --out-dir reports/weekly
```

### Target Files

```text
src/conflux/weekly/
  __init__.py
  composer.py
  report.py

tests/test_weekly_report.py
```

### Acceptance Criteria

- Weekly report can run from offline fixtures.
- Report includes literature, knowledge base updates, progress audit, risks, and next actions.
- Report links each claim to paper, file, commit, test, or artifact refs.
- Empty sections render as explicit "no new evidence" messages.

### Tests

- `test_weekly_report_combines_papers_and_progress`
- `test_weekly_report_handles_empty_paper_inbox`
- `test_weekly_report_handles_missing_progress_baseline`

### Non-Goals

- Calendar integration.
- Email or messaging delivery.

## 13. R8: Trust And Evaluation Expansion

Priority: P2  
Goal: make quality measurable as the product grows.

### Functions To Implement

- Add paper relevance labeled fixture set.
- Add paper ingestion decision eval.
- Add source-type coverage metrics.
- Add progress evidence coverage metric.
- Add prompt-injection fixture from paper text.
- Add token and cost ledger for paper radar and Q&A runs.

### Acceptance Criteria

- Eval command reports paper relevance precision on fixture set.
- Eval command reports ingestion decision agreement.
- Eval command reports citation coverage for local paper answers.
- Progress audit reports percentage of claims with evidence refs.
- Prompt-injection fixture does not change system behavior.

### Tests And Commands

```powershell
python scripts/eval_paper_radar.py --offline
python scripts/eval_progress_audit.py --offline
python scripts/eval_reports.py --offline
```

### Non-Goals

- Human annotation tool.
- Online A/B testing.

## 14. R9: UI And Product Polish

Priority: P3  
Goal: make the workflow easier to demo after the core engine is reliable.

### Candidate Features

- Simple TUI for choosing profile, running paper radar, and opening reports.
- Minimal local web dashboard for paper inbox and progress audit.
- Evidence trace viewer.
- One-command demo script.

### Acceptance Criteria

- UI does not hide source status or uncertainty.
- UI uses existing JSON/Markdown outputs instead of duplicating logic.
- CLI remains fully usable without UI.

## 15. Recommended Implementation Order

1. R1 Research Profile
2. R2 Paper Ingestion Core
3. R3 Paper Radar and Inbox
4. R4 RAG Promotion
5. R6 Progress Audit MVP
6. R5 Evidence Q&A Integration
7. R7 Weekly Research Report
8. R8 Trust and Evaluation Expansion
9. R9 UI and Product Polish

Reasoning:

- Research Profile is the configuration root for every other module.
- Paper ingestion and inbox create the first visible user value.
- RAG promotion connects the new product layer back to Conflux's existing strength.
- Progress Audit is the main differentiator and should land before UI work.
- Weekly Report becomes compelling only after papers and progress both work.

R4.5 exception:

- A thin local workbench is allowed before R5/R6 because it reviews existing R1-R4 outputs instead of replacing core logic.
- The workbench must call existing Python pipelines and read generated JSON/Markdown/HTML artifacts.
- It must not become a full SaaS UI, and CLI workflows must remain first-class.

## 16. First Sprint Proposal

Sprint duration: 1 week  
Sprint goal: make `ResearchProfile` real and create deterministic paper ingestion fixtures.

### Sprint Tasks

- Add `src/conflux/research_profile/`.
- Add profile dataclass and YAML loader.
- Add `profiles/example_gis_agent.yaml`.
- Add profile validation tests.
- Add `src/conflux/paper_ingestion/models.py`.
- Add offline paper fixture loader.
- Add `tests/fixtures/papers/arxiv_sample.json`.
- Add paper record normalization tests.

### Sprint Acceptance

- `python -m pytest -q` passes.
- A valid profile can be loaded from CLI or direct function call.
- A paper fixture can be loaded into `PaperRecord` objects.
- No real API key or network access is needed.
- Docs mention the first sprint result.

## 17. Current Implementation And Test Nodes

Status after R6:

- R1 Research Profile is implemented with typed profile loading, validation, AcademyHunter-style profile mapping, and CLI entrypoints.
- R2 Paper Ingestion Core is implemented with offline fixtures, arXiv query planning/search, record normalization, deduplication, and negative filtering.
- R3 Paper Radar and Inbox is implemented with deterministic relevance scoring, offline analysis, reading-level assignment, Markdown inbox, and JSON inbox.
- R4 RAG Promotion is implemented with explicit ingestion policy, `LocalPaper` metadata, citation refs, reviewable promoted paper documents, optional Chroma indexing, and optional AcademyHunter-style PDF download/full-text chunk support.
- R4.5 Local Research Workbench is implemented with a no-extra-dependency local web UI for paper inbox, promotion review, report browsing, model probing, and real query execution with temporary custom API URL/key/model overrides.
- R6 进度审计 MVP 已实现：支持本地 Git、测试、研究产物和报告采集，基线对比，证据引用约束，Markdown/JSON 输出，以及工作台审计界面。
- R6.1 多项目进度监控已实现：`projects/*.yaml` 项目注册表、只读本地/远程 Git 版本检查、非 Git 研究目录、结构化目标与阶段计划、待确认的文档计划候选、手动刷新 API，以及统一项目面板。
- R6.1 的 Git 边界是纯监控，不执行 `pull`、`push`、`checkout` 或 `fetch`。远程对象不在本地时只提示无法精确比较，不隐式修改仓库。
- 项目配置是目标和计划的权威来源；文档提取结果只能作为 `pending_confirmation` 候选。
- 刷新策略已预留 `schedule_enabled`、`interval_minutes`、`last_refreshed_at` 和 `next_refresh_at`，首期不启动调度器。

Hands-on test points:

```powershell
python -m conflux.profile validate profiles/example_gis_agent.yaml
python -m conflux.papers crawl --profile profiles/example_gis_agent.yaml --source arxiv --dry-run
python -m conflux.papers inbox --profile profiles/example_gis_agent.yaml --fixture tests/fixtures/papers/arxiv_sample.json --out-dir reports/papers_demo
python -m conflux.papers promote reports/papers_demo/paper_inbox.json --out-dir data/documents/papers
python -m conflux.progress snapshot --profile profiles/example_gis_agent.yaml --out-dir reports/progress
python -m conflux.progress audit --profile profiles/example_gis_agent.yaml --since last --out-dir reports/progress
python -m conflux.workbench --host 127.0.0.1 --port 8765
```

Optional real-run gates:

```powershell
python -m conflux.papers inbox --profile profiles/example_gis_agent.yaml --source arxiv --max-results 10 --out-dir reports/papers_real
python -m conflux.papers promote reports/papers_real/paper_inbox.json --out-dir data/documents/papers --full-text --pdf-dir data/documents/papers/pdfs --download-pdfs
python -m conflux.papers promote reports/papers_real/paper_inbox.json --out-dir data/documents/papers --index
```

The optional commands may require network access and configured embedding credentials. They must remain opt-in and should not be part of default offline tests.
