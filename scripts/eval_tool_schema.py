"""工具契约 Schema 校验评测（确定性）。

加载内置插件声明的工具/能力（CapabilitySpec.input_schema），对每个能力：
- 生成符合 schema 的合法输入 → validate_capability_input 应放行（issues 为空）
- 生成类型错误 / 缺必填字段的非法输入 → 应被拒绝（issues 非空）
- 生成结构错误的“工具调用”（错误类型 + 多余字段）→ 应被拒绝

聚合：Schema 通过率（合法输入放行率）、非法输入拒绝率、无效工具调用拦截率。
所有判断走真实 jsonschema 校验路径（core/policy.validate_capability_input）。

用法:
    python scripts/eval_tool_schema.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from conflux.adapters.plugin_loader import load_builtin_plugins  # noqa: E402
from conflux.core.policy import validate_capability_input  # noqa: E402
from conflux.core.registry import get_registry  # noqa: E402


def _sample_value(typ: str, spec: dict | None = None):
    if typ == "array" and spec:
        item = spec.get("items", {})
        it = item.get("type", "string")
        if it == "object":
            return [_sample_value("object", item)]
        return [_sample_value(it, item)]
    if typ == "object" and spec:
        props = spec.get("properties", {})
        return {k: _sample_value(v.get("type", "string"), v) for k, v in props.items()}
    return {
        "string": "sample",
        "integer": 3,
        "number": 1.5,
        "boolean": True,
        "array": ["a"],
        "object": {"k": "v"},
    }.get(typ, "sample")


def _valid_input(schema: dict) -> dict:
    props = schema.get("properties", {})
    required = schema.get("required", [])
    out = {}
    for name, spec in props.items():
        if name in required or spec.get("default") is not None or len(out) < 2:
            out[name] = _sample_value(spec.get("type", "string"), spec)
    for name in required:
        if name not in out:
            out[name] = _sample_value(props.get(name, {}).get("type", "string"), props.get(name, {}))
    return out


def _invalid_inputs(schema: dict) -> list[tuple[str, dict]]:
    props = schema.get("properties", {})
    required = schema.get("required", [])
    out = []
    # 1) 必填字段类型错误
    if required:
        name = required[0]
        spec = props.get(name, {})
        good = _sample_value(spec.get("type", "string"))
        bad = "not_a_number" if isinstance(good, (int, float)) else 12345
        bad_input = _valid_input(schema)
        bad_input[name] = bad
        out.append((f"type_error:{name}", bad_input))
    # 2) 缺必填字段
    if required:
        name = required[0]
        bad_input = _valid_input(schema)
        bad_input.pop(name, None)
        out.append((f"missing:{name}", bad_input))
    # 3) 结构错误工具调用：整型塞给字符串必填 + 多余未知字段
    if required:
        name = required[0]
        bad_input = _valid_input(schema)
        bad_input[name] = 999
        bad_input["__garbage_field__"] = {"nested": True}
        out.append(("malformed_call", bad_input))
    return out


def main() -> int:
    registry = load_builtin_plugins(get_registry())
    caps = registry.list_capabilities()

    rows = []
    valid_total = valid_pass = 0
    invalid_total = invalid_caught = 0
    malformed_total = malformed_caught = 0

    for cap_id in caps:
        record = registry.get_capability(cap_id)
        spec = None
        for c in record.manifest.capabilities:
            if c.id == cap_id:
                spec = c
                break
        if spec is None:
            continue
        schema = spec.input_schema or {}
        # 合法输入
        vinput = _valid_input(schema)
        vissues = validate_capability_input(vinput, schema)
        valid_total += 1
        if not vissues:
            valid_pass += 1
        # 非法输入
        for label, iinput in _invalid_inputs(schema):
            invalid_total += 1
            iissues = validate_capability_input(iinput, schema)
            caught = bool(iissues)
            if caught:
                invalid_caught += 1
            if label == "malformed_call":
                malformed_total += 1
                if caught:
                    malformed_caught += 1
            rows.append({
                "capability": cap_id,
                "case": label,
                "schema_passed": not vissues,
                "invalid_caught": caught,
                "issues": iissues[:2],
            })

    result = {
        "capability_count": len(caps),
        "valid_input_total": valid_total,
        "valid_input_pass": valid_pass,
        "schema_pass_rate": round(valid_pass / valid_total, 4) if valid_total else None,
        "invalid_input_total": invalid_total,
        "invalid_input_caught": invalid_caught,
        "invalid_rejection_rate": round(invalid_caught / invalid_total, 4) if invalid_total else None,
        "malformed_call_total": malformed_total,
        "malformed_call_caught": malformed_caught,
        "invalid_tool_call_intercept_rate": round(malformed_caught / malformed_total, 4) if malformed_total else None,
        "capabilities": caps,
        "rows": rows,
    }
    out = PROJECT_ROOT / "reports" / "eval" / "tool_schema" / "tool_schema.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("capabilities", "rows")}, ensure_ascii=False, indent=2))
    print(f"wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
