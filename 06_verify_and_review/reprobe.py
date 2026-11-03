"""Re-verify cases that stopped at the 'api' tier (booted, but the probe call failed) with the current probe, which
runs inside the app's container using the app's own gradio_client. No Beam call: the patch is Beam's saved one.
The case records that it was re-verified, with the old and new probe results.
usage: reprobe.py [space_id ...]   (default: every case at tier 'api')"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, re, shutil, sys
from pathlib import Path

import sandbox

ROOT = Path("/data/repro")


def run(d: Path):
    case = json.load(open(d / "case.json"))
    rec = json.load(open(d / "repro.json"))
    sid = case["space"]
    k = next(i for i, a in enumerate(case["attempts"]) if a["stage"] in ("api", "functional"))
    att = case["attempts"][k]
    orig = sandbox.SPACES_ROOT / d.name / "orig"
    if not orig.exists():
        sandbox.fetch_space(sid, orig)
    tree = sandbox.SPACES_ROOT / d.name / "reprobe"
    shutil.rmtree(tree, ignore_errors=True)
    shutil.copytree(orig, tree, ignore=shutil.ignore_patterns("Dockerfile.spacedoctor"))
    for f in (d / "fixed").rglob("*"):  # Beam's patched files over the full original (which keeps the weights)
        if f.is_file():
            dst = tree / f.relative_to(d / "fixed")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, dst)
    fm = sandbox.front_matter((tree / "README.md").read_text(errors="replace"))
    fmeta = dict(fm, _python=fm.get("python_version") or rec["meta"].get("_python"))
    outs = d / "outputs_reprobe"
    shutil.rmtree(outs, ignore_errors=True)
    res = sandbox.build_and_test(tree, fmeta, tag="sd-rp-" + re.sub(r"[^a-z0-9]", "-", sid.lower())[:50], outdir=outs)
    ok = res["stage"] == "running" and res.get("functional")
    if not ok and att["stage"] == "functional":  # a stricter check failed: downgrade, and say so
        att.update(stage="api", downgraded=True, probe=res.get("probe"))
        case.update(tier="api", revived=True)
    case["reprobe"] = {"attempt": k, "old_probe": att.get("probe"), "new_probe": res.get("probe"), "stage": res["stage"], "logs": sandbox.tail(res.get("logs", ""), 3000),
                       "functional": bool(ok), "note": "re-verified with the app's own gradio_client; patch unchanged"}
    if ok:
        att.update(stage="functional", probe=res.get("probe"), reprobed=True)
        case.update(tier="functional", revived=True)
        shutil.rmtree(d / "outputs", ignore_errors=True)
        if outs.exists():
            shutil.copytree(outs, d / "outputs")
    json.dump(case, open(d / "case.json", "w"), indent=1)
    print(f"{sid:55s} reprobe functional={bool(ok)} stage={res['stage']} "
          f"{[(p.get('endpoint'), p.get('ok'), (p.get('error') or '')[:80]) for p in res.get('probe') or []]}", flush=True)


if __name__ == "__main__":
    dirs = [ROOT / s.replace("/", "__") for s in sys.argv[1:]] or \
        [d for d in sorted(ROOT.iterdir()) if (d / "case.json").exists() and json.load(open(d / "case.json")).get("tier") == "api"
         and "reprobe" not in json.load(open(d / "case.json"))]
    import concurrent.futures as cf, os
    with cf.ThreadPoolExecutor(int(os.environ.get("SD_WORKERS", "4"))) as ex:
        list(ex.map(run, dirs))
