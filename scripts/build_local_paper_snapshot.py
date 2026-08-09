"""Build a PaperRecord candidate snapshot from local knowledge-base summaries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    payload: dict = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            payload[key.strip()] = value.strip()
    return payload


def _section(text: str, name: str) -> str:
    pattern = rf"^## {name}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.S | re.M)
    return match.group(1).strip() if match else ""


def _metadata_value(text: str, label: str) -> str:
    match = re.search(rf"^- {label}:\s*(.*)$", text, re.M)
    return match.group(1).strip() if match else ""


def _parse_summary(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    front = _frontmatter(text)
    title = re.search(r"^# (.+)$", text, re.M)
    authors = _metadata_value(text, "Authors")
    published = _metadata_value(text, "Published")
    categories = _metadata_value(text, "Categories")
    return {
        "id": front.get("paper_id") or path.stem.split("#")[0],
        "title": title.group(1).strip() if title else path.stem,
        "abstract": _section(text, "Abstract"),
        "authors": [item.strip() for item in authors.split(",") if item.strip()],
        "published_at": published or None,
        "source": "arxiv",
        "url": _metadata_value(text, "URL"),
        "pdf_url": _metadata_value(text, "PDF"),
        "doi": "",
        "venue": "",
        "categories": [item.strip() for item in categories.split(",") if item.strip()],
        "matched_queries": [],
        "metadata": {"source_file": str(path)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local paper candidate snapshot")
    parser.add_argument("--source-dir", default=str(PROJECT_ROOT / "data" / "documents" / "papers" / "papers"))
    parser.add_argument("--output", default=str(PROJECT_ROOT / "evaluation" / "kg_llm_radar" / "candidates_local_20260809.jsonl"))
    args = parser.parse_args(argv)

    source_dir = Path(args.source_dir)
    rows = []
    for path in sorted(source_dir.glob("*#summary.md")):
        payload = _parse_summary(path)
        if payload["id"] and payload["title"]:
            rows.append(payload)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote: {output} ({len(rows)} candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
