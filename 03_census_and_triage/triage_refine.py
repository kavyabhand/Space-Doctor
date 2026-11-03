"""Second triage pass: Beam sees only the logs its first taxonomy did not match, plus that taxonomy, and proposes
additional families (or corrected regexes). Code re-measures coverage over all logs; nothing here is self-reported.
usage: triage_refine.py [census] [triage.json] [--reuse]"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, re, sys

import beam
# Same log cleaning as pass 1 (copied, not imported: importing triage.py would run its Beam call).
TAIL = 600
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\[A")
PROGRESS = re.compile(r"[^\n|]*(?:it/s|MB/s|kB/s|%\|)[^\n|]*")


def clean(err):
    e = ANSI.sub("", err or "")
    e = PROGRESS.sub("", e)
    e = re.sub(r"[ \t]+", " ", e)
    e = re.sub(r"\n\s*\n+", "\n", e)
    return e.strip()[-TAIL:]

CENSUS = sys.argv[1] if len(sys.argv) > 1 else "/data/census.json"
T1 = sys.argv[2] if len(sys.argv) > 2 else "/data/triage.json"
RAW = T1.replace(".json", "_refine_raw.json")

rows = [r for r in json.load(open(CENSUS)) if r["stage"] in ("RUNTIME_ERROR", "BUILD_ERROR", "CONFIG_ERROR") and r["err"]
        and r["err"] != "FETCHFAIL"]
logs = {r["id"]: clean(r["err"]) for r in rows}
likes = {r["id"]: r["likes"] for r in rows}
t1 = json.load(open(T1))
missed = [sid for sid in logs if sid not in t1["assignment"]]
corpus = "\n".join(f"<<{sid}>>\n{logs[sid]}" for sid in missed)
known = json.dumps([{k: f.get(k) for k in ("name", "regex", "fixable_in_code")} for f in t1["families"]], indent=0)

prompt = f"""You earlier grouped the error logs of broken Hugging Face Spaces into root-cause families, each with a
Python regex. We ran your regexes over all {len(logs)} logs. They matched {len(logs) - len(missed)}; the {len(missed)} logs
below matched none of them.

Your first families:
{known}

Propose ADDITIONAL families that cover the unmatched logs (or a corrected regex for an existing family whose
regex was too narrow; reuse its exact name then). Same fields as before: "name", "regex" (Python, applied with
re.search and re.S to each cleaned log), "fixable_in_code", "typical_fix", "example_ids". Prefer exact exception
text over vague words. Return ONLY JSON: {{"families": [...]}}

UNMATCHED LOGS:
{corpus}"""

if "--reuse" in sys.argv:
    r = json.load(open(RAW))
else:
    print(f"{len(missed)} unmatched logs, prompt ~{len(prompt) // 4} tokens", flush=True)
    r = beam.chat([{"role": "user", "content": prompt}], effort="high", max_tokens=32000, tag="triage-refine")
    json.dump(r, open(RAW, "w"))
text = r["content"]
m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
new = json.JSONDecoder().raw_decode(m.group(1) if m else text[text.find("{"):])[0]["families"]

# Merge: a refined family with an existing name replaces that family's regex.
fam = {f["name"]: dict(f, round=1) for f in t1["families"]}
for f in new:
    if f.get("name") in fam:
        fam[f["name"]].update({k: f[k] for k in ("regex", "typical_fix") if f.get(k)}, round="1+2")
    else:
        fam[f.get("name", f"family {len(fam)}")] = dict(f, round=2)
fam = list(fam.values())

assigned = {}
for f in fam:
    try:
        rx = re.compile(f.get("regex") or "(?!)", re.S)
    except re.error as e:
        f["regex_error"], f["matched"], f["first_match_only"] = str(e), 0, 0
        continue
    hits = [sid for sid, log in logs.items() if rx.search(log)]
    f["matched"], f["first_match_only"] = len(hits), 0
    for sid in hits:
        if sid not in assigned:
            assigned[sid] = f["name"]
            f["first_match_only"] += 1
for f in fam:
    f["likes"] = sum(likes[s] for s, n in assigned.items() if n == f["name"])
report = {"n_logs": len(logs), "covered": len(assigned), "coverage": round(len(assigned) / len(logs), 3),
          "coverage_round1": t1["coverage"],
          "fixable_in_code_spaces": sum(f["first_match_only"] for f in fam if f.get("fixable_in_code")),
          "fixable_in_code_likes": sum(f["likes"] for f in fam if f.get("fixable_in_code")),
          "usage": [t1["usage"], r["usage"]], "secs": [t1["secs"], r["secs"]], "families": fam, "assignment": assigned}
json.dump(report, open(T1, "w"), indent=1)
print(json.dumps({k: v for k, v in report.items() if k not in ("families", "assignment")}, indent=1))
for f in sorted(fam, key=lambda f: -f.get("first_match_only", 0))[:45]:
    print(f"{f.get('first_match_only', 0):5d} r{f.get('round')} {str(f.get('fixable_in_code')):5s} {f['name']}")
