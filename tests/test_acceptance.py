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
