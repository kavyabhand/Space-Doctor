"""One-screen progress: cases by tier, Beam budget used, reproduction count."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json
from collections import Counter
from pathlib import Path
root = Path("/data/repro")
cases = [json.load(open(d / "case.json")) for d in root.iterdir() if (d / "case.json").exists()]
repro = [json.load(open(d / "repro.json")) for d in root.iterdir() if (d / "repro.json").exists()]
base = [json.load(open(d / "baseline.json")) for d in root.iterdir() if (d / "baseline.json").exists()]
t = Counter(c.get("tier") or ("unfixable" if c["attempts"] and c["attempts"][-1]["stage"] == "declared_unfixable" else "failed") for c in cases)
print(f"cases {len(cases)}: {dict(t)}  likes revived {sum(c['likes'] for c in cases if c.get('tier') == 'functional')}")
print("revived:", sorted((c['likes'], c['space']) for c in cases if c.get('tier') == 'functional')[::-1])
print(f"repro {len(repro)}: broken {sum(r['our_stage'] in ('runtime_error', 'build_error') for r in repro)}")
print(f"baseline {len(base)}: {dict(Counter(b.get('tier') for b in base))}")
L = [json.loads(l) for l in open("/data/beam_ledger.jsonl")] if Path("/data/beam_ledger.jsonl").exists() else []
print(f"beam calls {len(L)}  out {sum(l['usage'].get('completion_tokens', 0) for l in L)}  in {sum(l['usage'].get('prompt_tokens', 0) for l in L)}  remaining {L[-1]['remaining'] if L else None}")
