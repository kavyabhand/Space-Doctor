"""One-call triage: Beam reads the error log of every broken Space in the census (~0.5M tokens) and
proposes failure families as regex signatures. The regexes are then run over the logs by code, so the
coverage numbers in the report are measured, not claimed by the model."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, re, sys

import beam

CENSUS = sys.argv[1] if len(sys.argv) > 1 else "/data/census.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/data/triage.json"
TAIL = 600

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\[A")
PROGRESS = re.compile(r"[^\n|]*(?:it/s|MB/s|kB/s|%\|)[^\n|]*")


def clean(err):
    e = ANSI.sub("", err or "")
    e = PROGRESS.sub("", e)
    e = re.sub(r"[ \t]+", " ", e)
    e = re.sub(r"\n\s*\n+", "\n", e)
    return e.strip()[-TAIL:]


rows = [r for r in json.load(open(CENSUS)) if r["stage"] in ("RUNTIME_ERROR", "BUILD_ERROR", "CONFIG_ERROR") and r["err"]
        and r["err"] != "FETCHFAIL"]
logs = {r["id"]: clean(r["err"]) for r in rows}
corpus = "\n".join(f"<<{i}|{r['id']}|{r['stage']}|{r['sdk']}|{r['hw']}>>\n{logs[r['id']]}" for i, r in enumerate(rows))

prompt = f"""Below are the error logs (last {TAIL} characters each) of {len(rows)} broken Hugging Face Spaces,
taken from the 10,000 most-liked Spaces. Each starts with <<index|space id|stage|sdk|hardware>>.

Group them into root-cause families. For each family give:
- "name": short label
- "regex": a Python regex that matches the logs of this family and as few others as possible
  (it will be run with re.search and re.S over each cleaned log; keep it specific, e.g. an exact exception message)
- "fixable_in_code": true if an author could fix it by editing the repo (deps/code/config), false if it is
  platform, hardware, quota, secrets, or a dead external service
- "typical_fix": one sentence
- "example_ids": up to 3 space ids from the logs

Aim for 20-40 families that together cover most logs, ordered by size. Return ONLY JSON:
{{"families": [...]}}

LOGS:
{corpus}"""

print(f"{len(rows)} logs, prompt ~{len(prompt) // 4} tokens", flush=True)
RAW = OUT.replace(".json", "_raw.json")
if len(sys.argv) > 3 and sys.argv[3] == "--reuse":  # re-parse a saved answer without another call
    r = json.load(open(RAW))
else:
    r = beam.chat([{"role": "user", "content": prompt}], effort="high", max_tokens=32000, tag="triage")
    json.dump(r, open(RAW, "w"))  # keep Beam's answer before parsing, so a parse bug never costs a second call
text = r["content"]
m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
fam = json.JSONDecoder().raw_decode(m.group(1) if m else text[text.find("{"):])[0]["families"]

# Measure: which logs does each proposed signature actually match?
assigned = {}
for f in fam:
    try:
        rx = re.compile(f.get("regex") or "(?!)", re.S)  # a family without a regex matches nothing
    except re.error as e:
        f["regex_error"] = str(e)
        f["matched"] = f["first_match_only"] = 0
        continue
    hits = [sid for sid, log in logs.items() if rx.search(log)]
    f["matched"] = len(hits)
    f["first_match_only"] = 0
    for sid in hits:
        if sid not in assigned:
            assigned[sid] = f["name"]
            f["first_match_only"] += 1
likes = {r["id"]: r["likes"] for r in rows}
for f in fam:
    f["likes"] = sum(likes[s] for s, n in assigned.items() if n == f["name"])
covered = len(assigned)
report = {"n_logs": len(rows), "covered": covered, "coverage": round(covered / len(rows), 3),
          "fixable_in_code_spaces": sum(f["first_match_only"] for f in fam if f.get("fixable_in_code")),
          "usage": r["usage"], "secs": r["secs"], "families": fam,
          "assignment": assigned}
json.dump(report, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in report.items() if k not in ("families", "assignment")}, indent=1))
for f in sorted(fam, key=lambda f: -f.get("first_match_only", 0)):
    print(f"{f.get('first_match_only', 0):5d} {str(f.get('fixable_in_code')):5s} {f['name']}")
