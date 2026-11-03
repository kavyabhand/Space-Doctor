"""List revivals that have no review yet, with risk flags, so a human reads the risky ones closely.
usage: review_queue.py FINAL_DIR"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, re, sys
from pathlib import Path

F = Path(sys.argv[1] if len(sys.argv) > 1 else "final")
reviews = json.load(open(Path(__file__).parent / "reviews.json"))
REQ = re.compile(r"^[+-]\s*[A-Za-z0-9_.\-\[\]]+\s*(@\s*\S+|(==|>=|<=|~=|<|>)\S*)?\s*$")
SUSP_ADD = re.compile(r"\bexcept\b|\bpass\b|return None|mock|dummy|placeholder|stub|fake|os\.environ\.get\(|file_types|allow_any|skip", re.I)
BAD_OUT = re.compile(r"error|exception|traceback|please (provide|enter|upload|set)|api[ _-]?key|not found|invalid|rate limit|429|unauthori|forbidden|quota", re.I)

rows = []
for d in sorted((F / "repro").iterdir()):
    f = d / "case.json"
    if not f.exists():
        continue
    c = json.load(open(f))
    if c.get("tier") != "functional" or c["space"] in reviews:
        continue
    a = next(a for a in c["attempts"] if a["stage"] == "functional")
    diff = a.get("diff", "")
    files = re.findall(r"^\+\+\+ b/(.+)$", diff, re.M)
    code = [l for l in diff.splitlines() if re.match(r"^[+-](?![+-])", l)]
    cur = None
    code_lines = []
    for l in diff.splitlines():
        if l.startswith("+++ b/"):
            cur = l[6:]
        elif re.match(r"^[+-](?![+-])", l) and cur and not cur.endswith(("requirements.txt", "README.md", "packages.txt")):
            code_lines.append(l)
    probe = next((p for p in a.get("probe") or [] if p.get("ok") and not p.get("helper")), {})
    out = str(probe.get("output_summary") or "")
    flags = []
    if code_lines:
        flags.append(f"code:{len(code_lines)}")
    if any(SUSP_ADD.search(l) for l in code_lines if l.startswith("+")):
        flags.append("SUSPICIOUS-ADD")
    if BAD_OUT.search(out):
        flags.append("OUTPUT-LOOKS-LIKE-ERROR")
    if probe.get("inputs") and any(len(i) > 8 and i in out for i in probe["inputs"]):
        flags.append("echo?")
    if not probe.get("files") and len(out.strip(" '\"[]()")) < 4:
        flags.append("TRIVIAL-OUTPUT")
    if (probe.get("endpoint") or "").startswith("fn_index") or probe.get("via") == "legacy":
        flags.append("legacy")
    rows.append((c["likes"], c["space"], d.name, a.get("lock"), files, flags, code_lines, probe, a.get("diagnosis", "")))

for likes, sid, dn, lock, files, flags, code_lines, probe, diag in sorted(rows, key=lambda r: -r[0]):
    print(f"===== {sid} ({likes})  lock={lock['date'] if lock else '-'}  files={files}  FLAGS={flags or 'none'}")
    print("  diag:", diag[:260])
    if code_lines:
        print("  code:", "\n        ".join(code_lines[:14]))
    print(f"  probe {probe.get('endpoint')} via={probe.get('via')} in={[str(i)[-40:] for i in probe.get('inputs', [])][:3]}")
    print(f"  out: {str(probe.get('output_summary'))[:240]}  files={probe.get('files')}")
print(f"\n{len(rows)} unreviewed revivals")
