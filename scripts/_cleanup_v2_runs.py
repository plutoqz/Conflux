"""Clean up old V2 runs and keep only the latest per query."""
import json, glob, re
from pathlib import Path

latest = {}
for sf in sorted(glob.glob("reports/v2-h/*.summary.json")):
    s = json.loads(open(sf, encoding="utf-8").read())
    q = s.get("query", "").strip()
    if not q:
        continue
    # Keep the latest file per query
    if q not in latest or sf > latest[q][0]:
        latest[q] = (sf, s)

# Delete old files
all_files = set(glob.glob("reports/v2-h/*"))
keepers = {Path(latest[q][0]) for q in latest}
# Also keep .md, .html, .trace.jsonl for the latest run_id
for q, (sf, s) in latest.items():
    rid = s.get("run_id", "")
    for pattern in [f"*{rid}*"]:
        for f in glob.glob(f"reports/v2-h/{pattern}"):
            keepers.add(Path(f))

for f in sorted(all_files):
    if Path(f) not in keepers:
        Path(f).unlink(missing_ok=True)

# Print latest
for q, (sf, s) in latest.items():
    md = s.get("report_md_path", "")
    chars = len(Path(md).read_text(encoding="utf-8")) if md and Path(md).exists() else 0
    body = Path(md).read_text(encoding="utf-8") if md and Path(md).exists() else ""
    sections = len(re.findall(r"(?m)^## (?!直接|参考|可信|FactCheck|跨节)", body))
    timeouts = body.count("本节因生成超时或失败未能完成")
    print(f"{q[:40]:40s} | {sections:2d}s/{timeouts:1d}to | {chars:5d}chars | {s.get('confidence','?'):10s} | {s.get('run_status','?')}")
