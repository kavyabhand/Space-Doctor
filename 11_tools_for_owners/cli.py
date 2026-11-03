"""Space Doctor for one Space, on your machine: reproduce the failure, let Beam patch it, rebuild and verify.

    export REFLECTION_API_KEY=...        # free key from platform.reflection.ai
    python cli.py owner/space-name       # needs Docker with buildx; GPU Spaces: SD_GPU=1 and an NVIDIA GPU

Writes ./spacedoctor_runs/<owner>__<space>/{repro.json, case.json, fixed/}. Nothing is pushed anywhere.
Run open_pr.py on the result if you want to propose the fix (only allowed for verified fixes)."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, os, re, sys
from pathlib import Path

RUNS = Path(os.environ.get("SD_RUNS", "spacedoctor_runs")).resolve()
os.environ.setdefault("SD_WORK", str(RUNS / "_work"))
os.environ.setdefault("BEAM_LEDGER", str(RUNS / "beam_ledger.jsonl"))

import requests
import doctor, sandbox


def last_exc(err: str) -> str:
    lines = [l.strip() for l in (err or "").splitlines() if l.strip()]
    for l in reversed(lines):
        if re.match(r"^\w*(Error|Exception)\b|^\w+\.\w*(Error|Exception)\b|^\w+Error:", l):
            return l[:300]
    return lines[-1][:300] if lines else ""


def main(sid: str):
    sid = sid.removeprefix("https://huggingface.co/spaces/").strip("/")
    d = RUNS / sid.replace("/", "__")
    d.mkdir(parents=True, exist_ok=True)
    rt = requests.get(f"https://huggingface.co/api/spaces/{sid}/runtime", timeout=30).json()
    info = requests.get(f"https://huggingface.co/api/spaces/{sid}", timeout=30).json()
    err = rt.get("errorMessage") or ""
    print(f"{sid}: {rt.get('stage')} | {last_exc(err) or 'no public error'}")
    repo = sandbox.SPACES_ROOT / sid.replace("/", "__") / "orig"
    sandbox.fetch_space(sid, repo)
    meta = sandbox.front_matter((repo / "README.md").read_text(errors="replace")) if (repo / "README.md").exists() else {}
    meta["_python"] = sandbox.python_for(meta, err)
    print("Reproducing the failure in a Spaces-like rebuild ...")
    res = sandbox.build_and_test(repo, meta, tag="sd-orig-" + re.sub(r"[^a-z0-9]", "-", sid.lower())[:50])
    rec = {"space": sid, "likes": info.get("likes", 0),
           "meta": {k: v for k, v in meta.items() if k in ("sdk", "sdk_version", "python_version", "app_file", "_python")},
           "hf_error_tail": err[-4000:], "hf_exception": last_exc(err), "our_stage": res["stage"],
           "our_exception": last_exc(res.get("logs", "")), "same_exception": False,
           "our_logs": res.get("logs", ""), "api": res.get("api"), "secs": res.get("secs"), "freeze": res.get("freeze", "")}
    json.dump(rec, open(d / "repro.json", "w"), indent=1)
    if res["stage"] not in ("runtime_error", "build_error"):
        print(f"Our rebuild does not fail ({res['stage']}). The Hugging Face failure may be transient: try a restart.")
        return
    case = doctor.treat(d)
    print(json.dumps({k: case[k] for k in ("revived", "tier", "tokens", "wall_secs")}, indent=1))
    if case.get("tier") == "functional":
        print(f"Verified fix in {d / 'fixed'}. Review it, then: python open_pr.py {d}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
