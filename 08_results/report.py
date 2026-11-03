"""Aggregate census, reproductions, Beam case files, the no-LLM baseline and triage into one summary.json.
usage: report.py [DATA_DIR]   (DATA_DIR holds census.json, triage.json, repro/; default /data)"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, sys
from collections import Counter
from pathlib import Path

D = Path(sys.argv[1] if len(sys.argv) > 1 else "/data")
root = D / "repro"
census = json.load(open(D / "census.json"))
broken = [r for r in census if r["stage"] in ("RUNTIME_ERROR", "BUILD_ERROR", "CONFIG_ERROR")]
dirs = [d for d in sorted(root.iterdir()) if (d / "repro.json").exists()]
repros = [json.load(open(d / "repro.json")) for d in dirs]
cases = [json.load(open(d / "case.json")) for d in dirs if (d / "case.json").exists()]
REV = _ROOT / "06_verify_and_review" / "reviews.json"
reviews = json.load(open(REV)) if REV.exists() else {}
for c in cases:  # a human review can reject a probe-verified patch (e.g. it silently changed behaviour)
    v = reviews.get(c["space"], {}).get("verdict")
    if v == "rejected":
        c.update(tier="rejected", revived=False, review=reviews[c["space"]])
    elif v == "unverified" and c.get("tier") == "functional":
        c.update(tier="api", review=reviews[c["space"]])
base = {json.load(open(d / "repro.json"))["space"]: json.load(open(d / "baseline.json")) for d in dirs if (d / "baseline.json").exists()}
calls = [c for case in cases for c in case["calls"]]

def tier(c):
    return c.get("tier") or ("unfixable" if c["attempts"] and c["attempts"][-1]["stage"] == "declared_unfixable" else "failed")

fixed_at = Counter()
for c in cases:
    if c.get("tier") == "functional":
        k = next(i for i, a in enumerate(c["attempts"]) if a["stage"] == "functional")
        fixed_at[f"{c['attempts'][k]['effort']} (attempt {k + 1})"] += 1

both = [c for c in cases if c["space"] in base]
cmp = Counter((tier(c) == "functional", base[c["space"]].get("tier") == "functional") for c in both)

summary = {
    "census": {"date": "2026-10-30", "spaces": len(census), "broken": len(broken), "broken_likes": sum(r["likes"] for r in broken),
               "stages": Counter(r["stage"] for r in census)},
    "reproduction": {"attempted": len(repros), "still_broken": sum(r["our_stage"] in ("runtime_error", "build_error") for r in repros),
                     "same_exception_as_hf": sum(bool(r["same_exception"]) for r in repros),
                     "stages": Counter(r["our_stage"] for r in repros)},
    "treatment": {"treated": len(cases), "gpu_cases": sum(bool(c.get("gpu")) for c in cases),
                  "tiers": Counter(tier(c) for c in cases),
                  "declared_unfixable": sum(tier(c) == "unfixable" for c in cases),
                  "rejected_at_review": [{"space": c["space"], "reason": c["review"]["reason"]} for c in cases if c.get("tier") == "rejected"],
                  "reprobed": sum(1 for c in cases if c.get("reprobe")),
                  "guard_rejections": sum(a["stage"] == "rejected_by_integrity_guard" for c in cases for a in c["attempts"]),
                  "likes_revived": sum(c["likes"] for c in cases if c.get("tier") == "functional"),
                  "fixed_at": fixed_at,
                  "beam_calls": len(calls),
                  "prompt_tokens": sum((c["usage"] or {}).get("prompt_tokens", 0) for c in calls),
                  "cached_prompt_tokens": sum(((c["usage"] or {}).get("prompt_tokens_details") or {}).get("cached_tokens", 0) for c in calls),
                  "completion_tokens": sum((c["usage"] or {}).get("completion_tokens", 0) for c in calls),
                  "median_beam_secs": sorted(c["secs"] for c in calls)[len(calls) // 2] if calls else None,
                  "median_wall_secs": sorted(c["wall_secs"] for c in cases)[len(cases) // 2] if cases else None},
    "baseline": {"name": "time-travel pinning (uv --exclude-newer <last commit>, Python 3.10 unless pinned)",
                 "compared": len(both),
                 "beam_only": cmp[(True, False)], "baseline_only": cmp[(False, True)],
                 "both": cmp[(True, True)], "neither": cmp[(False, False)],
                 "baseline_tiers": Counter(b.get("tier") for b in base.values())},
}
tri = D / "triage.json"
if tri.exists():
    t = json.load(open(tri))
    # A catch-all is judged by breadth, not by its name: a regex that matches >= 20% of all logs is not a diagnosis.
    catch_all = [f for f in t["families"] if f.get("matched", 0) >= 0.2 * t["n_logs"]]
    specific = t["covered"] - sum(f.get("first_match_only", 0) for f in catch_all)
    summary["triage"] = {"n_logs": t["n_logs"], "coverage_round1": t.get("coverage_round1", t["coverage"]),
                         "coverage_reported": t["coverage"], "coverage_specific": round(specific / t["n_logs"], 3),
                         "catch_all_families": [{"name": f["name"], "regex": f.get("regex"), "matched": f["first_match_only"],
                                                 "matched_any": f["matched"]} for f in catch_all],
                         "families": len(t["families"]),
                         "prompt_tokens": [u.get("prompt_tokens") for u in (t["usage"] if isinstance(t["usage"], list) else [t["usage"]])],
                         "secs": t["secs"]}
json.dump(summary, open(D / "summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
for c in sorted(cases, key=lambda c: -c["likes"]):
    a = c["attempts"][-1] if c["attempts"] else {}
    b = base.get(c["space"], {}).get("tier", "-")
    print(f"{c['likes']:5d} {c['space']:50s} {tier(c):11s} base={b:13s} {len(c['attempts'])} att | {a.get('category')} | {(a.get('diagnosis') or '')[:100]}")
