"""GPU track (run on the A10G box with SD_GPU=1): reproduce famous GPU Spaces broken by code drift, then treat them.
A10G is the GPU of HF's a10g-small; t4/l4 Spaces are verified on it too (noted per case)."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, os, sys, concurrent.futures as cf

IDS, sys.argv = sys.argv[1:], sys.argv[:1]  # reproduce.py reads sys.argv at import
import reproduce, doctor, beam
census = {r["id"]: r for r in reproduce.CENSUS}

def go(sid):
    d = reproduce.OUT / sid.replace("/", "__")
    try:
        if not (d / "repro.json").exists():
            reproduce.run(census[sid])
        rec = json.load(open(d / "repro.json"))
        if rec["our_stage"] not in ("runtime_error", "build_error"):
            print(f"{sid}: not broken in our rebuild ({rec['our_stage']}), skipped", flush=True); return
        if not (d / "case.json").exists():
            doctor.treat(d)
    except beam.BudgetExhausted as e:
        print(f"{sid}: BUDGET STOP {e}", flush=True)
    except Exception as e:
        print(f"{sid}: harness error {e!r}", flush=True)

with cf.ThreadPoolExecutor(int(os.environ.get("SD_WORKERS", "2"))) as ex:
    list(ex.map(go, IDS))
