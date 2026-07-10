# Graduate Research Copilot Product Spec

> Working name: Graduate Research Copilot  
> Repository base: Conflux  
> Related local reference project: `F:\vscode\AcademyHunter`  
> Target version: MVP for computer science, AI, GIS, and engineering graduate students

## 1. Product Positioning

Graduate Research Copilot is a local-first AI research workbench for graduate students who are simultaneously reading papers, building code, running experiments, and writing research artifacts.

The product should not be positioned as a generic chatbot. Its core value is evidence-centered research assistance:

- discovering relevant papers continuously;
- promoting high-value literature into a traceable knowledge base;
- answering research questions with explicit source separation;
- auditing real progress across code, experiments, reports, and repositories.

The first version should serve graduate students in computer science, AI, GIS, and engineering fields, especially those whose work combines literature review, code implementation, experiments, and thesis writing.

## 2. Target Users

Primary user:

- A master's or PhD student in CS, AI, GIS, remote sensing, software engineering, data science, or related engineering fields.
- Maintains one or more code repositories.
- Reads papers regularly but struggles to track relevance, reuse, and citation value.
- Uses AI coding tools and needs help distinguishing real progress from superficial generated changes.
- Needs reproducible research records for thesis, papers, meetings, and advisor updates.

Secondary user:

- Early-career researcher managing multiple small research ideas.
- Lab member preparing weekly paper reports or progress reports.
- Student building a thesis topic from a moving literature landscape.

Non-target users for MVP:

- Users who only want a general mental-health companion.
- Users who need a full SaaS lab-management platform.
- Users in domains requiring strict clinical, legal, or financial compliance.
- Users whose research workflow has no papers, code, experiments, or local artifacts.

## 3. MVP Scope

The MVP has four required loops.

### 3.1 Research Profile

A user defines their research context once, then iterates it over time.

The profile should include:

- research area;
- active research questions;
- keywords and query templates;
- negative filters;
- target venues or journals;
- tracked scholars or groups;
- local project paths;
- relevant local document folders;
- preferred report cadence.

Output:

- a normalized profile object used by paper search, RAG filtering, and progress auditing.

### 3.2 Paper Radar

The system periodically searches paper sources, filters irrelevant papers, analyzes promising papers, and creates a reading inbox.

MVP sources:

- arXiv first;
- Semantic Scholar or DBLP later;
- manual PDF import as a fallback.

The paper radar should produce:

- new papers;
- deduplicated paper records;
- relevance score;
- reading level: `deep`, `skim`, or `skip`;
- citation usefulness;
- method or dataset reuse potential;
- ingestion decision for the knowledge base.

AcademyHunter already contains most of the first implementation:

- arXiv crawler;
- research profile configuration;
- negative filtering;
- L1 embedding relevance scoring;
- L2 LLM scoring;
- deep analysis;
- PDF download;
- report generation;
- SQLite and Chroma persistence.

Conflux should not import AcademyHunter as a monolith. It should absorb or wrap the useful parts behind a stable paper ingestion interface.

### 3.3 Evidence RAG

High-value papers and local documents become structured knowledge sources.

The RAG layer must distinguish:

- paper metadata;
- abstract-level evidence;
- full-text PDF chunks;
- user notes;
- project documents;
- generated analysis summaries.

Not every crawled paper should enter the vector database. The ingestion policy should be explicit:

- `skip`: store only metadata or ignore;
- `metadata_only`: keep paper metadata for future rediscovery;
- `summary_only`: store abstract and LLM analysis;
- `full_text`: download and index PDF text;
- `pinned`: force include by user decision.

Research Q&A must expose source type:

- `LocalPaper`;
- `LocalNote`;
- `ProjectDoc`;
- `Web`;
- `ModelInference`.

The answer should preserve the existing Conflux discipline:

- chunk-level citations;
- source status: `success`, `low_relevance`, `no_evidence`, `failed`, `fallback`;
- failed or fallback sources excluded from evidence voting;
- uncertainty and evidence gaps shown explicitly.

### 3.4 Progress Audit

The system monitors real progress across research projects.

MVP inputs:

- local Git repositories;
- local result folders;
- experiment logs;
- Markdown or LaTeX reports;
- test outputs;
- optional remote Git metadata later.

Progress audit should answer:

- What actually changed since the last snapshot?
- Did tests or evaluations improve?
- Are there new experiment artifacts?
- Are claims in reports backed by result files?
- Did the project only accumulate AI-generated code without validation?
- Which tasks are blocked, stale, or inconsistent?

This is the most distinctive feature. It should not be reduced to commit counting. The product must inspect evidence of progress.

## 4. Deferred Features

The following features should be postponed until after the MVP:

- full web UI;
- SaaS multi-user accounts;
- complex knowledge graph persistence;
- automatic paper writing;
- full PDF figure and table understanding;
- Zotero integration;
- GitHub issue sync;
- Slack or WeChat notifications;
- therapist-style mental health companion.

A lightweight reflection module can be added later, but it should be framed as research reflection and cognitive offloading, not medical or therapeutic support.

## 5. System Architecture

Recommended module layout:

```text
src/conflux/
  research_profile/
    models.py
    loader.py
    validators.py

  paper_ingestion/
    models.py
    arxiv_source.py
    scorer.py
    analyzer.py
    ingestion_policy.py
    pipeline.py

  knowledge/
    source_models.py
    paper_indexer.py
    note_indexer.py
    citation_resolver.py

  progress_audit/
    models.py
    git_inspector.py
    artifact_inspector.py
    test_inspector.py
    report_inspector.py
    auditor.py

  rag/
    chunker.py
    indexer.py
    retriever.py

  tools/
    rag.py
    web.py
    model.py
    papers.py
    progress.py
```

Existing Conflux modules should remain responsible for:

- RAG retrieval;
- web search;
- model source;
- evidence graph;
- arbitration;
- FactCheck;
- trace and run summary;
- Markdown and HTML reports.

New modules should feed structured evidence into the existing graph instead of bypassing it.

## 6. Core Data Contracts

The following interfaces define the product boundary. Field names should remain stable even if implementation changes.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class ResearchProfile:
    id: str
    name: str
    fields: list[str]
    research_questions: list[str]
    keywords: list[str]
    negative_keywords: list[str] = field(default_factory=list)
    target_venues: list[str] = field(default_factory=list)
    tracked_scholars: list[str] = field(default_factory=list)
    project_paths: list[str] = field(default_factory=list)
    document_paths: list[str] = field(default_factory=list)


@dataclass
class PaperRecord:
    id: str
    title: str
    abstract: str
    authors: list[str]
    published_at: datetime | None
    source: str
    url: str = ""
    pdf_url: str = ""
    venue: str = ""
    categories: list[str] = field(default_factory=list)


@dataclass
class PaperAnalysis:
    paper_id: str
    relevance_score: float
    reading_level: Literal["deep", "skim", "skip"]
    matched_questions: list[str]
    method_summary: str
    novelty: str
    reusable_methods: list[str] = field(default_factory=list)
    reusable_datasets: list[str] = field(default_factory=list)
    citation_value: Literal["high", "medium", "low"] = "medium"
    limitations: str = ""


@dataclass
class IngestionDecision:
    paper_id: str
    action: Literal["skip", "metadata_only", "summary_only", "full_text", "pinned"]
    reason: str
    priority: int = 0


@dataclass
class KnowledgeSource:
    id: str
    source_type: Literal["LocalPaper", "LocalNote", "ProjectDoc", "Web", "ModelInference"]
    title: str
    locator: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ProjectSnapshot:
    project_id: str
    path: str
    captured_at: datetime
    git_branch: str = ""
    git_head: str = ""
    dirty_files: list[str] = field(default_factory=list)
    recent_commits: list[str] = field(default_factory=list)
    test_status: str = "unknown"
    result_files: list[str] = field(default_factory=list)
    report_files: list[str] = field(default_factory=list)


@dataclass
class ProgressAuditReport:
    project_id: str
    period: str
    real_progress: list[str]
    weak_signals: list[str]
    risks: list[str]
    recommended_next_actions: list[str]
    evidence_refs: list[str]
```

## 7. End-to-End Data Flow

```text
ResearchProfile
  -> Paper Radar
  -> PaperRecord + PaperAnalysis
  -> IngestionDecision
  -> KnowledgeSource
  -> RAG Index
  -> Evidence Q&A
  -> Report + Trace + Evidence Graph

Local Projects
  -> ProjectSnapshot
  -> ProgressAuditReport
  -> Evidence Q&A / Weekly Progress Report
```

The system should always preserve provenance:

- where a paper came from;
- why it was selected;
- whether it entered the knowledge base;
- which chunk supported an answer;
- which file, commit, test, or artifact supported a progress claim.

## 8. Product Workflows

### 8.1 Weekly Literature Workflow

1. User defines or updates research profile.
2. Paper Radar crawls sources.
3. System deduplicates papers.
4. System scores relevance.
5. Deep papers are analyzed.
6. User sees a weekly reading inbox.
7. High-value papers are indexed into RAG.
8. System emits a literature update report.

Acceptance criteria:

- at least one deterministic offline fixture can simulate the pipeline;
- paper relevance score and ingestion decision are visible;
- indexed papers are queryable with citations.

### 8.2 Research Question Workflow

1. User asks a research question.
2. Conflux dispatches RAG, Web, and Model agents.
3. Local paper evidence is separated from web evidence and model inference.
4. Evidence graph and source statuses are generated.
5. FactCheck verifies that failed sources are not used as evidence.
6. Markdown and HTML reports are produced.

Acceptance criteria:

- answer cites paper chunks when available;
- model-only claims are marked as inference;
- no failed source enters evidence voting.

### 8.3 Progress Audit Workflow

1. User registers one or more project paths.
2. System creates baseline snapshots.
3. On demand or weekly, system scans changes.
4. System compares code changes, tests, logs, result files, and reports.
5. System produces a progress audit report.

Acceptance criteria:

- report distinguishes real progress from weak activity signals;
- every progress claim has a file, commit, test, or artifact reference;
- stale or unvalidated AI-generated changes are flagged.

## 9. Quality Gates

The project should keep Conflux's existing quality posture and extend it.

Required gates:

- unit tests for data contracts;
- offline paper ingestion fixture;
- retrieval eval over sample paper corpus;
- report acceptance checks;
- failed-source leakage test;
- prompt-injection fixture from paper text;
- progress audit fixture with known Git/test/artifact changes.

Suggested metrics:

- paper deduplication hit rate;
- relevance precision on a small labeled set;
- ingestion decision accuracy;
- RAG citation coverage;
- failed-source leakage;
- progress audit evidence coverage;
- average time per weekly run;
- estimated token and API cost.

## 10. Implementation Roadmap

### Week 1: Productization Foundation

- Add this product spec.
- Add `ResearchProfile` schema.
- Convert one AcademyHunter profile into a Conflux-compatible profile fixture.
- Add tests for profile loading and validation.

### Week 2: Paper Ingestion Interface

- Add `PaperRecord`, `PaperAnalysis`, and `IngestionDecision`.
- Wrap or port AcademyHunter arXiv crawler.
- Add offline paper fixtures.
- Add deterministic deduplication and negative filtering tests.

### Week 3: Paper Scoring and Inbox

- Add L1 relevance scoring.
- Add L2 optional LLM scoring behind a real-run flag.
- Generate a paper inbox Markdown report.
- Keep all real API calls opt-in.

### Week 4: RAG Promotion

- Implement ingestion policy.
- Index selected paper summaries and optional PDFs.
- Ensure chunk citations include paper metadata.
- Add retrieval eval for the paper corpus.

### Week 5: Evidence Q&A Integration

- Add a paper search tool or enrich existing RAG metadata.
- Ensure answers distinguish `LocalPaper`, `Web`, and `ModelInference`.
- Extend report appendix with paper citation details.

### Week 6: Progress Audit MVP

- Add Git inspector.
- Add artifact/result file inspector.
- Add test status inspector.
- Generate `ProgressAuditReport`.
- Add offline fixture repository for audit tests.

### Week 7: Weekly Research Report

- Combine paper inbox and progress audit into one weekly report.
- Add run summary JSON for product-level reports.
- Add examples suitable for README and resume demonstration.

### Week 8: Polish and Demo

- Add concise README section for Graduate Research Copilot mode.
- Add demo commands.
- Add sample reports.
- Run tests and offline eval.
- Prepare resume bullets and interview explanation.

## 11. Resume Narrative

Short version:

> Built a local-first graduate research copilot that ingests papers, promotes high-relevance literature into an evidence-traced RAG knowledge base, answers research questions with source-aware arbitration, and audits real project progress across code, experiments, and reports.

Technical version:

> Extended Conflux into a graduate research workbench with paper ingestion, relevance scoring, ingestion policies, chunk-level paper citations, RAG/Web/Model evidence arbitration, FactCheck verification, structured run traces, and progress auditing over Git repositories and experiment artifacts.

Interview explanation order:

1. Graduate research is not just Q&A; it is an evidence-management problem.
2. Paper discovery feeds a local knowledge base through explicit ingestion decisions.
3. Answers separate local paper evidence, web evidence, and model inference.
4. Progress audit inspects code, tests, results, and reports instead of trusting activity signals.
5. Evaluation covers retrieval quality, failed-source leakage, citation coverage, and progress evidence coverage.

## 12. Main Risks

Scope risk:

- The product can easily become too broad. Keep MVP focused on literature, evidence Q&A, and progress audit.

Data quality risk:

- Automatically indexed papers can pollute the knowledge base. Use explicit ingestion decisions and metadata filters.

Trust risk:

- The system must avoid presenting model inference as evidence. Preserve Conflux's source status protocol.

Cost risk:

- Daily LLM analysis can become expensive. Use L1 cheap filtering before deep analysis.

Progress audit risk:

- Superficial code changes are easy to summarize but hard to judge. Require evidence references for every progress claim.

## 13. MVP Completion Criteria

The MVP is complete when all of the following are true:

- A user can define one research profile.
- The system can crawl or load sample papers.
- The system can score and report paper relevance.
- The system can decide which papers enter the knowledge base.
- The system can answer a research question using local paper evidence.
- The system can produce a progress audit for at least one local repository.
- Generated reports include citations, source status, and uncertainty.
- Offline tests and eval commands run without real API keys.
- Real API runs are opt-in and documented.

