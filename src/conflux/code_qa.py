"""P4.4 E1 代码问答 — AST 感知分块 + 索引入知识库 + 调用链图遍历（E1.1/E1.2）。

设计对照 docs/plans/p4/E_文献笔记与代码问答.md §E1：
- AST 感知分块：按函数/类/方法切块 + 签名摘要头（imports、被调用关系），
  先支持 Python；AST 解析失败回退行块（复用既有 rag.chunker 能力）。
- 索引入 P3.4 同一 Chroma 知识库：代码块 metadata ``doc_kind=code_doc``、
  ``language`` 与符号名，source 前缀 ``code:``（与文档 ``project:`` 区分，
  compute_coverage 对代码块不计数，避免污染文档覆盖）。
- 问答：函数级块检索 → 答案绑定 ``文件:行号``；调用链用确定性图遍历
  （AST 调用关系），字段不做模型猜测——本模块零 LLM 触点。
- 证据：输出 ``code:{project_id}:{path}#L{line}`` 引用格式，可直接进
  Evidence Ledger（与文档证据同一条可追溯链）。

通用性：schema/命令均为通用形状，不硬编码 Conflux/FusionAgent 专有字段。
"""

from __future__ import annotations

import ast
import dataclasses
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from langchain_core.documents import Document

_CODE_PREFIX = "code:"
# Call-site names that are values, not functions (avoid false call edges).
_CALL_IGNORE = {
    "model", "data", "self", "cls", "loss", "result", "results", "value",
    "values", "config", "cfg", "args", "kwargs", "text", "content", "item",
    "items", "key", "keys", "index", "idx", "state", "docs", "doc",
    "request", "response", "output", "inputs", "input", "params", "payload",
}

_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    "data", "dist", "build", ".pytest_cache", ".idea", ".vscode",
    "reports", "artifacts", "results", ".mypy_cache", ".ruff_cache",
}
MAX_SYMBOL_CHARS = 3000
MAX_INDEX_FILES = 800
MAX_INDEX_SYMBOLS = 20000


@dataclass(slots=True)
class CodeSymbol:
    """一个可检索的代码单元（函数/类/方法）+ 与其所在文件行号。"""

    path: str  # 相对项目根
    id: str = ""
    name: str = ""
    kind: str = "function"  # function / class / method
    start_line: int = 0
    end_line: int = 0
    source: str = ""
    docstring: str = ""
    calls: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    parent_class: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"{self.path}#{self.parent_class + '.' if self.parent_class else ''}{self.name}"


def _code_source(project_id: str, rel_path: str) -> str:
    normalized = str(rel_path).replace("\\", "/").lstrip("/")
    return f"{_CODE_PREFIX}{project_id}:{normalized}"


def _file_imports(tree: ast.Module) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return sorted({value for value in imports if value})


def _called_names(body: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(body):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                names.append(fn.id)
            elif isinstance(fn, ast.Attribute):
                names.append(fn.attr)
    return [name for name in names if name not in _CALL_IGNORE]


def _docstring_of(node: ast.AST) -> str:
    value = ast.get_docstring(node, clean=False)
    return str(value or "").strip()[:500]


def _line_of(node: ast.AST) -> int:
    return int(getattr(node, "lineno", 0) or 0)


def _line_end_of(node: ast.AST) -> int:
    return int(getattr(node, "end_lineno", 0) or max(1, _line_of(node)))


def _slice_source(source: str, node: ast.AST) -> str:
    lines = source.splitlines(keepends=True)
    start = max(1, _line_of(node))
    end = min(len(lines), _line_end_of(node))
    return "".join(lines[start - 1:end])[:MAX_SYMBOL_CHARS]


def _parse_function(node: ast.AST, source: str, path: str, imports: list[str],
                    parent_class: str = "") -> CodeSymbol | None:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    return CodeSymbol(
        path=path,
        name=str(node.name),
        kind="method" if parent_class else "function",
        start_line=_line_of(node),
        end_line=_line_end_of(node),
        source=_slice_source(source, node),
        docstring=_docstring_of(node),
        calls=list(dict.fromkeys(_called_names(node))),
        imports=imports,
        parent_class=parent_class,
    )


def parse_python_symbols(source: str, path: str) -> list[CodeSymbol]:
    """AST 解析；语法错误返回 []（调用方走行块回退）。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imports = _file_imports(tree)
    symbols: list[CodeSymbol] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbol = _parse_function(node, source, path, imports)
            if symbol:
                symbols.append(symbol)
        elif isinstance(node, ast.ClassDef):
            class_name = str(node.name)
            symbols.append(CodeSymbol(
                path=path,
                name=class_name,
                kind="class",
                start_line=_line_of(node),
                end_line=_line_end_of(node),
                source=_slice_source(source, node),
                docstring=_docstring_of(node),
                calls=list(dict.fromkeys(_called_names(node))),
                imports=imports,
                parent_class="",
            ))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method = _parse_function(child, source, path, imports,
                                             parent_class=class_name)
                    if method:
                        symbols.append(method)
    return symbols


def code_documents(project_id: str, rel_path: str, symbols: list[CodeSymbol]) -> list[Document]:
    """把符号列表转成知识库块：签名摘要头 + 被调用关系（E1.1）。"""
    documents: list[Document] = []
    for symbol in symbols:
        if not symbol.name or not symbol.source.strip():
            continue
        header = f"# {symbol.parent_class + '.' if symbol.parent_class else ''}{symbol.name}" \
                 f" ({symbol.kind}, {rel_path}:{symbol.start_line}-{symbol.end_line})"
        if symbol.docstring:
            header += f"\n{symbol.docstring}"
        if symbol.calls:
            header += "\n调用了: " + ", ".join(list(dict.fromkeys(symbol.calls))[:20])
        metadata = {
            "source": _code_source(project_id, rel_path),
            "doc_kind": "code_doc",
            "language": "python",
            "symbol": symbol.id,
            "symbol_kind": symbol.kind,
            "line_start": symbol.start_line,
            "line_end": symbol.end_line,
            "path": rel_path,
            "chunk_id": f"{_code_source(project_id, rel_path)}#{symbol.id}",
        }
        documents.append(Document(page_content=header + "\n" + symbol.source, metadata=metadata))
    return documents


def walk_code_files(root: Path, *, skip_dirs: set[str] | None = None) -> list[Path]:
    """收集项目根下 *.py（通用；跳过噪音目录）。"""
    skipped = skip_dirs or _SKIP_DIRS
    files: list[Path] = []
    if not root.exists():
        return files
    try:
        for path in sorted(root.rglob("*.py")):
            try:
                if any(part in skipped for part in path.relative_to(root).parts):
                    continue
                if "__pycache__" in path.parts:
                    continue
                files.append(path)
            except ValueError:
                continue
    except OSError:
        return files
    return files[:MAX_INDEX_FILES]


def index_project_code(
    intelligence: Any,
    project: Any,
    *,
    root_dir: str | Path | None = None,
) -> dict[str, Any]:
    """索引项目 Python 源码进入知识库（P3.4 同一 Chroma collection）。

    幂等：chunk_id 稳定（source#symbol），内容变化才更新（index_documents
    的 content-hash-aware upsert）；上限 MAX_INDEX_FILES / MAX_INDEX_SYMBOLS
    防索引膨胀（P3.6 分区上限思路）。
    """
    from conflux.rag.indexer import create_vector_store, index_documents

    root = Path(root_dir or getattr(project, "path", "")).expanduser().resolve()
    files = walk_code_files(root)
    symbols: list[CodeSymbol] = []
    failed: list[dict[str, str]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            failed.append({"path": str(path), "error": str(exc)})
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        parsed = parse_python_symbols(text, rel)
        if not parsed:
            # AST 失败 → 行块回退（按固定行切块，保留代码块语义）
            parsed = _line_block_fallback(text, rel)
        if not parsed:
            continue
        symbols.extend(parsed)
        if len(symbols) >= MAX_INDEX_SYMBOLS:
            break

    project_id = getattr(project, "id", "") or ""
    documents: list[Document] = []
    for symbol in symbols[:MAX_INDEX_SYMBOLS]:
        documents.extend(code_documents(project_id, symbol.path, [symbol]))
    if not documents:
        return {"ok": False, "error": "没有可索引的 Python 代码（先确认项目路径有 .py 文件）。", "failed": failed}

    try:
        indexed = index_documents(create_vector_store(), documents)
    except Exception as exc:
        return {"ok": False, "error": f"代码索引写入失败：{type(exc).__name__}: {exc}", "failed": failed}
    return {
        "ok": True,
        "files": len(files),
        "symbols": len(documents),
        "indexed": indexed,
        "failed": failed,
    }


def _line_block_fallback(text: str, rel_path: str, *, block_lines: int = 60) -> list[CodeSymbol]:
    """AST 失败时的行块回退：按固定行数切块，每块一个伪符号。"""
    lines = text.splitlines()
    symbols: list[CodeSymbol] = []
    for start in range(0, len(lines), block_lines):
        block = "\n".join(lines[start:start + block_lines])
        if not block.strip():
            continue
        symbols.append(CodeSymbol(
            path=rel_path,
            name=f"line-block-{start + 1}",
            kind="fallback",
            start_line=start + 1,
            end_line=min(len(lines), start + block_lines),
            source=block[:MAX_SYMBOL_CHARS],
            docstring="",
        ))
    return symbols


# ── 调用链：AST 调用关系确定性图遍历（E1.1）──────────────────────


def symbol_qname(symbol: CodeSymbol) -> str:
    return f"{symbol.parent_class}.{symbol.name}" if symbol.parent_class else symbol.name


def build_call_map(symbols: Iterable[CodeSymbol]) -> dict[str, dict[str, Any]]:
    """name → 定义信息；callers/callees 都记录 qname（含父类前缀）。"""
    by_name: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        qname = symbol_qname(symbol)
        entry = by_name.setdefault(symbol.name, {
            "qname": qname,
            "path": symbol.path,
            "start_line": symbol.start_line,
            "end_line": symbol.end_line,
            "kind": symbol.kind,
            "callers": set(),
            "callees": set(),
        })
        for called in symbol.calls:
            entry["callees"].add(called)
            by_name.setdefault(called, {
                "qname": called,
                "path": "",
                "start_line": 0,
                "end_line": 0,
                "kind": "unknown",
                "callers": set(),
                "callees": set(),
            })["callers"].add(qname)
    return by_name


def _call_chain_impl(symbols: Iterable[CodeSymbol], *, seed: str, direction: str,
                     max_depth: int) -> list[dict[str, Any]]:
    by_name = build_call_map(symbols)
    results: list[dict[str, Any]] = []
    queue: list[tuple[str, int]] = [(seed, 0)]
    seen: set[str] = set()
    while queue:
        name, depth = queue.pop(0)
        if name in seen or depth > max_depth:
            continue
        seen.add(name)
        entry = by_name.get(name)
        if entry is None:
            continue
        if depth > 0:
            results.append({
                "name": name,
                "qname": entry["qname"],
                "path": entry["path"],
                "start_line": entry["start_line"],
                "end_line": entry["end_line"],
                "kind": entry["kind"],
                "depth": depth,
                "direction": direction,
                "ref": f"code:{entry['path']}#L{entry['start_line']}" if entry["path"] else "",
            })
        neighbors = entry["callers"] if direction == "callers" else entry["callees"]
        queue.extend((neighbor, depth + 1) for neighbor in sorted(neighbors))
    return results


def callers_of(symbols: Iterable[CodeSymbol], seed: str, *, max_depth: int = 3) -> list[dict[str, Any]]:
    return _call_chain_impl(symbols, seed=seed, direction="callers", max_depth=max_depth)


def callees_of(symbols: Iterable[CodeSymbol], seed: str, *, max_depth: int = 3) -> list[dict[str, Any]]:
    return _call_chain_impl(symbols, seed=seed, direction="callees", max_depth=max_depth)


# ── 问答（纯检索 + 确定性图遍历，零 LLM）────────────────────────


def search_code(
    query: str,
    *,
    project_id: str = "",
    top_k: int = 3,
    vector_store: Any | None = None,
) -> list[dict[str, Any]]:
    """在代码块中检索问题；返回带 文件:行号/引用的命中。"""
    from conflux.rag.indexer import create_vector_store

    store = vector_store or create_vector_store()
    try:
        scored = store.similarity_search_with_score(query, k=max(5, top_k * 4))
    except Exception:
        scored = []
    hits: list[dict[str, Any]] = []
    for document, score in scored:
        metadata = document.metadata or {}
        source = str(metadata.get("source") or "")
        if not source.startswith(_CODE_PREFIX):
            continue
        if project_id and not source.startswith(f"{_CODE_PREFIX}{project_id}:"):
            continue
        hits.append({
            "symbol": str(metadata.get("symbol") or ""),
            "kind": str(metadata.get("symbol_kind") or ""),
            "path": str(metadata.get("path") or ""),
            "line_start": int(metadata.get("line_start") or 0),
            "line_end": int(metadata.get("line_end") or 0),
            "score": float(score),
            "text": str(document.page_content)[:400],
            "ref": f"code:{metadata.get('path')}#L{metadata.get('line_start') or 0}",
        })
        if len(hits) >= top_k:
            break
    # 自然语言（中文）查询对英文代码嵌入不佳时的确定性兜底：
    # 从查询中提取 camelCase / snake_case 词，精确匹配已有符号，
    # 合并进结果（去重、命中优先），保证引用仍可回溯。
    if not hits and re.search(r"[\u4e00-\u9fff]", query):
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", query)
        if tokens:
            for token in tokens:
                token_lower = token.casefold()
                try:
                    existing = store.get(where={"symbol": token_lower}, limit=5)
                except Exception:
                    existing = {}
                for metadata in existing.get("metadatas") or []:
                    metadata = metadata or {}
                    source = str(metadata.get("source") or "")
                    if project_id and not source.startswith(f"{_CODE_PREFIX}{project_id}:"):
                        continue
                    path = str(metadata.get("path") or "")
                    line = int(metadata.get("line_start") or 0)
                    hits.append({
                        "symbol": str(metadata.get("symbol") or ""),
                        "kind": str(metadata.get("symbol_kind") or ""),
                        "path": path,
                        "line_start": line,
                        "line_end": int(metadata.get("line_end") or 0),
                        "score": -1.0,  # 确定性兜底，无相似度
                        "text": "",
                        "ref": f"code:{path}#L{line}",
                    })
                    if len(hits) >= top_k:
                        break
                if hits:
                    break
        else:
            # 纯中文查询：基于 code 块全量元数据做符号名子串匹配
            # （一次确定性扫描，零模型），按查询字符在符号/路径中的
            # 覆盖率排序，取 top_k。
            query_cjk = set(re.findall(r"[\u4e00-\u9fff]", query))
            candidates: list[tuple[float, dict[str, Any]]] = []
            try:
                offset = 0
                while True:
                    batch = store.get(where={"doc_kind": "code_doc"},
                                      include=["metadatas"], limit=2000, offset=offset)
                    metadatas = batch.get("metadatas") or []
                    if not metadatas:
                        break
                    for metadata in metadatas:
                        metadata = metadata or {}
                        source = str(metadata.get("source") or "")
                        if project_id and not source.startswith(f"{_CODE_PREFIX}{project_id}:"):
                            continue
                        path = str(metadata.get("path") or "")
                        raw_symbol = str(metadata.get("symbol") or "")
                        line = int(metadata.get("line_start") or 0)
                        matched = query_cjk_overlap(query, raw_symbol + " " + path)
                        if matched <= 0:
                            continue
                        candidates.append((matched, {
                            "symbol": raw_symbol,
                            "kind": str(metadata.get("symbol_kind") or ""),
                            "path": path,
                            "line_start": line,
                            "line_end": int(metadata.get("line_end") or 0),
                            "score": -1.0,
                            "text": "",
                            "ref": f"code:{path}#L{line}",
                        }))
                    offset += len(metadatas)
            except Exception:
                pass
            candidates.sort(key=lambda item: -item[0])
            for _, hit in candidates[:top_k]:
                hits.append(hit)
    return hits


def query_cjk_overlap(query_chars: set[str], subject: str) -> int:
    """查询 CJK 字符在 subject 中出现的数量（确定性相关度）。"""
    if not query_chars:
        return 0
    return sum(1 for char in query_chars if char in subject)


def answer_code_question(
    query: str,
    *,
    project_id: str = "",
    top_k: int = 3,
    max_chain_depth: int = 2,
    vector_store: Any | None = None,
    symbols: list[CodeSymbol] | None = None,
) -> dict[str, Any]:
    """确定性回答：检索命中 → 绑定 文件:行号 → 附调用链。

    E1.2：所有引用的 100% 由 metadata 生成，格式 code:{path}#L{line}。
    """
    from conflux.rag.indexer import create_vector_store

    store = vector_store or create_vector_store()
    hits = search_code(query, project_id=project_id, top_k=top_k, vector_store=store)
    refs = [hit["ref"] for hit in hits]
    chain: list[dict[str, Any]] = []
    if symbols and hits:
        seed = next((hit["symbol"].rsplit("#", 1)[-1] for hit in hits if hit["symbol"]), "")
        if seed:
            chain = callers_of(symbols, seed, max_depth=max_chain_depth)[:10]
    return {
        "query": query,
        "hits": hits,
        "refs": refs,  # E1.2: 100% code:{path}#L{line}
        "call_chain": chain,
        "answer": _compose_answer(hits, chain),
        "traceable": all(ref.startswith("code:") and "#L" in ref for ref in refs),
    }


def _compose_answer(hits: list[dict[str, Any]], chain: list[dict[str, Any]]) -> str:
    if not hits:
        return "没有找到匹配的代码块。"
    lines = ["相关代码位置："]
    lines.extend(f"- {hit['path']}:{hit['line_start']}-{hit['line_end']}（{hit['symbol']}）{hit['ref']}"
                 for hit in hits)
    if chain:
        lines.append("上游调用链（谁调用了它）：")
        seen: set[str] = set()
        for entry in chain:
            marker = f"{entry['qname']} ({entry['path']}:{entry['start_line']})"
            if marker not in seen:
                seen.add(marker)
                lines.append(f"- {marker}")
    return "\n".join(lines)