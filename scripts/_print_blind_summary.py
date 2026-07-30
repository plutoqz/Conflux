"""Print blind review summary table."""
import json

br = json.load(open("reports/evaluation/blind_reviews.json", encoding="utf-8"))

print(f"{'case_id':30s} | {'V2':>4s} | {'P15':>4s} | winner | breadth depth ev_correct synth")
print("-" * 85)
for r in br:
    v2_avg = sum(r["scores"].values()) / 6
    p15_avg = sum(r["p1_scores"].values()) / 6
    pw = r["p1_comparison"]
    print(
        f"{r['case_id']:30s} | {v2_avg:4.1f} | {p15_avg:4.1f} | "
        f"{r['overall_winner']:6s} | "
        f"b={pw['breadth']:+d} d={pw['depth']:+d} "
        f"e={pw['evidence_correctness']:+d} s={pw['synthesis_insight']:+d}"
    )
