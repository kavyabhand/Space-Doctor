"""No-LLM baseline: can a broken Space be revived just by travelling back in time?

For each patient, rebuild the untouched repo with every package resolved as it was on the Space's last commit
(`uv pip install --exclude-newer <lastModified>`), on the Python the Space was written for (README pin, else 3.10,
the long-time Spaces default). Same boot + functional probe as the Beam fixes, so the two are directly comparable.
Writes repro/<space>/baseline.json."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, os, re, sys, concurrent.futures as cf
from pathlib import Path

import sandbox

ROOT = Path("/data/repro")
CENSUS = {r["id"]: r for r in json.load(open("/data/census.json"))}


def run(d: Path):
    rec = json.load(open(d / "repro.json"))
    sid = rec["space"]
    when = ((CENSUS.get(sid) or {}).get("lastModified") or "")[:19] + "Z"  # RFC 3339, no millis
    out = {"space": sid, "date": when}
    try:
        src = sandbox.SPACES_ROOT / sid.replace("/", "__") / "baseline_src"
        sandbox.fetch_space(sid, src)
        meta = sandbox.front_matter((src / "README.md").read_text(errors="replace")) if (src / "README.md").exists() else {}
        meta["_python"] = str(meta.get("python_version") or "3.10")
        res = sandbox.build_and_test(src, meta, tag="sd-base-" + re.sub(r"[^a-z0-9]", "-", sid.lower())[:50],
                                     timetravel=when, outdir=d / "baseline_outputs", boot_timeout=600)
        api_ok = res["stage"] == "running" and not str(res.get("api", "")).startswith("API_ERROR")
        tier = "functional" if api_ok and res.get("functional") else "api" if api_ok else res["stage"]
        out.update(python=meta["_python"], tier=tier, logs=sandbox.tail(res.get("logs", ""), 3000), probe=res.get("probe"))
    except Exception as e:
        out.update(tier="harness_error", logs=repr(e))
    json.dump(out, open(d / "baseline.json", "w"), indent=1)
    print(f"{sid:55s} baseline={out['tier']}", flush=True)


if __name__ == "__main__":
    dirs = [ROOT / s.replace("/", "__") for s in sys.argv[1:]] or \
        [d for d in sorted(ROOT.iterdir()) if (d / "repro.json").exists() and not (d / "baseline.json").exists()
         and json.load(open(d / "repro.json"))["our_stage"] in ("runtime_error", "build_error")]
    with cf.ThreadPoolExecutor(int(os.environ.get("SD_WORKERS", "4"))) as ex:
        list(ex.map(run, dirs))
