"""Print a compact view of case files: python show.py space_id [...] (or all)."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, sys
from pathlib import Path
root = Path("/data/repro")
ids = sys.argv[1:] or [d.name for d in sorted(root.iterdir()) if (d / "case.json").exists()]
for sid in ids:
    f = root / sid.replace("/", "__") / "case.json"
    if not f.exists():
        print(sid, "(no case yet)"); continue
    c = json.load(open(f))
    print(f"=== {c['space']} likes={c['likes']} revived={c['revived']} tier={c['tier']} tokens={c['tokens']} wall={c['wall_secs']}s")
    for a in c["attempts"]:
        print(f"  [{a['effort']}] {a['stage']} | {a.get('verdict')} | {a.get('category')} | {a['diagnosis'][:400]}")
        if a.get("diff"): print("    " + a["diff"][:1500].replace("\n", "\n    "))
        if a["stage"] not in ("functional",) and a.get("logs"): print("    LOG: " + a["logs"][-600:].replace("\n", "\n    "))
        for p in a.get("probe") or []:
            print(f"    probe {p.get('endpoint')} ok={p.get('ok')} helper={p.get('helper')} files={p.get('files')} out={str(p.get('output_summary',''))[:200]} err={str(p.get('error',''))[:200]}")
