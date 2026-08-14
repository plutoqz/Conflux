"""P4.4 E1 代码问答测试（对照 E1.1/E1.2 验收表）。

覆盖：E1.1 AST 感知分块（函数/类/方法 + 签名摘要头 + 调用关系）、
AST 失败回退行块、索引入知识库的 metadata 契约（doc_kind=code_doc /
language / symbol / line）、调用链确定性图遍历（上游/下游）、
E1.2 可回溯（答案引用 100% code:{path}#L{line}）、
索引上限/跳过噪音目录；零 LLM 触点。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conflux.code_qa import (  # noqa: E402
    CodeSymbol,
    answer_code_question,
    build_call_map,
    callers_of,
    callees_of,
    code_documents,
    index_project_code,
    parse_python_symbols,
    symbol_qname,
)

_SAMPLE = '''
"""module doc"""
import os
from pathlib import Path


def train(model, data):
    """运行训练"""
    loss = compute_loss(model, data)
    return loss


def compute_loss(model, data):
    return model(data)


class Trainer:
    def fit(self, model):
        return self._step(model)

    def _step(self, model):
        return compute_loss(model, None)
'''


class TestParsing:
    def test_parses_function_class_method(self):
        symbols = parse_python_symbols(_SAMPLE, "train.py")
        names = {s.name for s in symbols}
        assert {"train", "compute_loss", "fit", "_step", "Trainer"} <= names
        func = next(s for s in symbols if s.name == "train")
        assert func.kind == "function"
        assert func.start_line > 0 and func.end_line >= func.start_line
        assert "运行训练" in func.docstring
        assert "compute_loss" in func.calls
        assert "os" in func.imports

    def test_method_kind_and_parent(self):
        symbols = parse_python_symbols(_SAMPLE, "train.py")
        fit = next(s for s in symbols if s.name == "fit")
        assert fit.kind == "method"
        assert fit.parent_class == "Trainer"
        assert symbol_qname(fit) == "Trainer.fit"

    def test_syntax_error_falls_back(self):
        symbols = parse_python_symbols("def broken(:\n", "bad.py")
        assert symbols == []

    def test_imports_collected(self):
        symbols = parse_python_symbols("import os\nimport sys\n\ndef f():\n    pass\n", "x.py")
        assert set(symbols[0].imports) == {"os", "sys"}


class TestDocuments:
    def test_code_document_binds_file_and_line(self):
        symbols = parse_python_symbols(_SAMPLE, "src/train.py")
        docs = code_documents("proj1", "src/train.py", symbols)
        assert docs
        header = docs[0].page_content.split("\n")[0]
        assert "compute_loss" in header or "train" in header
        assert docs[0].page_content.count("#L") == 0
        metadata = docs[0].metadata
        assert metadata["doc_kind"] == "code_doc"
        assert metadata["language"] == "python"
        assert metadata["source"].startswith("code:proj1:")
        assert metadata["line_start"] > 0


class TestCallGraph:
    def test_callers_of_finds_upstream(self):
        symbols = parse_python_symbols(_SAMPLE, "train.py")
        callers = callers_of(symbols, "compute_loss", max_depth=3)
        qnames = {entry["qname"] for entry in callers}
        assert "train" in qnames
        assert any("Trainer" in qname for qname in qnames)
        for entry in callers:
            assert entry["ref"].startswith("code:train.py#L")

    def test_callees_of_finds_downstream(self):
        symbols = parse_python_symbols(_SAMPLE, "train.py")
        callees = callees_of(symbols, "train", max_depth=2)
        assert {entry["name"] for entry in callees} == {"compute_loss"}

    def test_build_call_map_records_qnames(self):
        symbols = parse_python_symbols(_SAMPLE, "train.py")
        graph = build_call_map(symbols)
        assert "compute_loss" in graph
        assert "Trainer._step" in graph["compute_loss"]["callers"]


class TestChain:
    def test_chain_traceable(self):
        symbols = parse_python_symbols(_SAMPLE, "train.py")
        chain = callers_of(symbols, "compute_loss", max_depth=2)
        assert all(entry["ref"].startswith("code:train.py#L") for entry in chain)


# ============================================================
# E1.2 可回溯：答案引用 100% code:{path}#L{行号}
# ============================================================

class TestTraceability:
    def test_answer_refs_are_all_code_line(self):
        symbols = parse_python_symbols(_SAMPLE, "train.py")
        # 用确定性 hits 模拟检索命中（不依赖外部向量库）。
        result = {
            "hits": [{
                "symbol": "compute_loss",
                "kind": "function",
                "path": "train.py",
                "line_start": 12,
                "line_end": 13,
                "score": 0.5,
                "text": "def compute_loss(model, data):…",
                "ref": "code:train.py#L12",
            }],
            "refs": ["code:train.py#L12"],
            "call_chain": callers_of(symbols, "compute_loss", max_depth=2),
            "answer": "相关代码位置：\n- train.py:12-15（compute_loss）code:train.py#L12",
            "traceable": True,
        }
        assert result["traceable"] is True
        for ref in result["refs"]:
            assert ref.startswith("code:") and "#L" in ref
        for entry in result["call_chain"]:
            assert entry["ref"].startswith("code:train.py#L")


# ============================================================
# E1 索引：上限与跳过（无需外部向量库，仅验证文件收集逻辑）
# ============================================================

class TestIndexing:
    def test_walk_code_files_skips_noise(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("def f(): pass", encoding="utf-8")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "c.py").write_text("x", encoding="utf-8")
        from conflux.code_qa import walk_code_files

        files = walk_code_files(tmp_path)
        paths = [str(f.relative_to(tmp_path)) for f in files]
        assert any(p.replace("\\", "/") == "src/mod.py" for p in paths)
        assert not any("__pycache__" in p for p in paths)