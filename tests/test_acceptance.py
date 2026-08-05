import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _write_pair(tmp_path, markdown: str):
    md = tmp_path / "report.md"
    html = tmp_path / "report.html"
    md.write_text(markdown, encoding="utf-8")
    html.write_text("<!doctype html><html><body>report</body></html>", encoding="utf-8")
    return md, html


def test_acceptance_passes_complete_report(tmp_path):
    from conflux.acceptance import validate_report_pair

    evidence = {
        "summary": {
            "total_nodes": 2,
            "source_counts": {"RAG": 1, "Model": 1},
        },
        "source_statuses": {
            "RAG": {"status": "success"},
            "Web": {"status": "failed"},
            "Model": {"status": "success"},
        },
        "nodes": [
            {"id": "r1", "source": "RAG", "claim": "Loop Engineering 强调反馈闭环。"},
            {"id": "m1", "source": "Model", "claim": "多智能体系统需要验证闭环。"},
        ],
    }
    markdown = f"""# Conflux 调研报告

## 最终报告
### 最终结论
- Loop Engineering 强调反馈闭环。[RAG][Model]

### 信息来源
RAG 与 Model 可用。

### 不确定性
Web failed，因此外部时效信息仍有不确定性。

### 证据摘要
RAG 与 Model 支持核心结论。

## 信息来源状态
| 来源 | 状态 | 详情 | 错误/说明 |
|---|---|---|---|
| RAG | success | local | ok |
| Web | failed | web | timeout |
| Model | success | model | ok |

## FactCheck 验证
### 确定性追溯检查
- success 来源：RAG, Model
- low_relevance 来源：无
- no_evidence/failed/fallback 来源：Web

## 证据摘要
- 证据节点总数：2

## 附录 A：证据图 JSON
```json
{json.dumps(evidence, ensure_ascii=False)}
```

## 运行摘要
- 模式：phase2

## 质量评分
- 总分：4.5 / 5
- 是否达标：是
"""
    md, html = _write_pair(tmp_path, markdown)

    result = validate_report_pair(md, html)

    assert result.passed


def test_acceptance_rejects_failed_source_evidence_node(tmp_path):
    from conflux.acceptance import validate_report_pair

    evidence = {
        "summary": {"total_nodes": 1, "source_counts": {"Web": 1}},
        "source_statuses": {
            "RAG": {"status": "success"},
            "Web": {"status": "failed"},
            "Model": {"status": "success"},
        },
        "nodes": [
            {"id": "w1", "source": "Web", "claim": "失败来源不应进入证据节点。"},
        ],
    }
    markdown = f"""# Conflux 调研报告

## 最终报告
### 最终结论
信息来源、不确定性和证据都有说明。

## 信息来源状态
| 来源 | 状态 | 详情 | 错误/说明 |
|---|---|---|---|
| RAG | success | local | ok |
| Web | failed | web | timeout |
| Model | success | model | ok |

## FactCheck 验证
### 确定性追溯检查
- success 来源：RAG, Model

## 证据摘要
- 证据节点总数：1

## 附录 A：证据图 JSON
```json
{json.dumps(evidence, ensure_ascii=False)}
```

## 运行摘要
- 模式：phase2

## 质量评分
- 是否达标：是
"""
    md, html = _write_pair(tmp_path, markdown)

    result = validate_report_pair(md, html)

    assert not result.passed
    assert any("no_evidence/failed/fallback 来源出现在证据节点" in issue for issue in result.issues)


def test_acceptance_allows_low_relevance_status_and_nodes(tmp_path):
    from conflux.acceptance import validate_report_pair

    evidence = {
        "summary": {"total_nodes": 1, "source_counts": {"RAG": 1}},
        "source_statuses": {
            "RAG": {"status": "low_relevance"},
            "Web": {"status": "no_evidence"},
            "Model": {"status": "success"},
        },
        "nodes": [
            {"id": "r1", "source": "RAG", "claim": "GIS 弱相关上下文。", "evidence_refs": ["[RAG:gis#chunk-001]"]},
        ],
    }
    markdown = f"""# Conflux 调研报告

## 最终报告
### 最终结论
信息来源、不确定性和证据都有说明。

## 信息来源状态
| 来源 | 状态 | 详情 | 错误/说明 |
|---|---|---|---|
| RAG | low_relevance | local | weak |
| Web | no_evidence | web | unrelated |
| Model | success | model | ok |

## FactCheck 验证
### 确定性追溯检查
- success 来源：Model
- low_relevance 来源：RAG
- no_evidence/failed/fallback 来源：Web

## 证据摘要
- 证据节点总数：1

## 附录 A：证据图 JSON
```json
{json.dumps(evidence, ensure_ascii=False)}
```

## 运行摘要
- 模式：phase2

## 质量评分
- 是否达标：是
"""
    md, html = _write_pair(tmp_path, markdown)

    result = validate_report_pair(md, html)

    assert result.passed


def test_v2_artifacts_include_evidence_and_pass_v2_acceptance(tmp_path):
    from conflux.acceptance import validate_report_pair
    from conflux.graph_v2 import factcheck_v2_node
    from conflux.report import write_v2_report_artifacts

    state = {
        "query": "如何构建可审计的研究智能体？",
        "_run_id": "run-v2-test",
        "_run_status": "completed",
        "_report_available": True,
        "_confidence": "high",
        "_elapsed_ms": 1200,
        "_report_markdown": """# 如何构建可审计的研究智能体？

## 直接回答

核心路径是保存来源、引用和验证记录。[1]

## 证据链设计

每个外部声明应关联可解析的来源。[1]

## 参考文献与证据

[1] 可审计系统保存证据来源。

## 可信度说明

该结论有一条外部证据支持。
""",
        "_direct_answer": "核心路径是保存来源、引用和验证记录。[1]",
        "_rag_results": "local evidence",
        "_web_results": "web evidence",
        "_citation_map": {"[1]": "可审计系统保存证据来源。（来源：RAG local.md#chunk-001）"},
        "_section_results": [{
            "sub_question_id": "sq-1",
            "title": "证据链设计",
            "body": "每个外部声明应关联可解析的来源。[1]",
            "summary": "",
            "key_claims": ["每个外部声明应关联可解析的来源。[1]"],
            "citation_refs": ["[1]"],
            "analysis_judgments": [],
            "evidence_gaps": [],
            "finish_reason": "complete",
        }],
        "_source_statuses": {
            "RAG": {"status": "success", "result_count": 1},
            "Web": {"status": "no_evidence", "result_count": 0},
            "Model": {"status": "success", "result_count": 1},
        },
        "_audit_metrics": {
            "total_sections": 1,
            "analysis_only_sections": 0,
            "invalid_citation_refs": 0,
        },
    }
    state.update(factcheck_v2_node(state, model=None))

    artifacts = write_v2_report_artifacts(state["query"], state, tmp_path)
    result = validate_report_pair(artifacts.markdown_path, artifacts.html_path)

    assert result.passed
    assert artifacts.evidence_json_path is not None
    assert artifacts.raw_sources_path is not None
    assert artifacts.audit_markdown_path is not None
    html = artifacts.html_path.read_text(encoding="utf-8")
    assert "核心路径是保存来源、引用和验证记录" in html
    assert "<title>如何构建可审计的研究智能体？</title>" in html
    assert state["_run_summary"]["factcheck_status"] == "passed"
    assert state["_run_summary"]["external_evidence_count"] == 1
