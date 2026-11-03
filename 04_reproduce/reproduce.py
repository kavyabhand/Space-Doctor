"""Pick code-level failures from the census and reproduce each one in the sandbox.
A Space only counts as a patient if our rebuild fails the same way Hugging Face's did."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, re, sys, concurrent.futures as cf
from pathlib import Path

import sandbox

CENSUS = json.load(open("/data/census.json"))
OUT = Path("/data/repro"); OUT.mkdir(exist_ok=True)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 6

# Failures that are not in the code: platform, hardware, quota, missing secrets, dead upstream services.
NOT_CODE = re.compile(r"containerd|[Ss]cheduling|Launch timed out|Memory limit|NVIDIA|CUDA|Could not resolve host|"
                      r"Exit code: \?|Error while cloning|HTTP Error 40[13]|Service Updating|token|api[_ ]key|"
                      r"OPENAI|secret|quota|ZeroGPU", re.I)


def last_exc(err: str) -> str:
    lines = [l for l in (err or "").splitlines() if l.strip()]
    for l in reversed(lines):
        if re.match(r"^\w*(Error|Exception)\b|^\w+\.\w*(Error|Exception)\b|^\w+Error:", l.strip()):
            return l.strip()[:300]
    return lines[-1].strip()[:300] if lines else ""


def candidates():
    out = []
    for r in sorted(CENSUS, key=lambda r: -r["likes"]):
        if r["stage"] != "RUNTIME_ERROR" or r["hw"] != "cpu-basic" or r["sdk"] not in ("gradio", "streamlit"):
            continue
        e = r["err"] or ""
        if not re.search(r"Traceback|Error", e) or NOT_CODE.search(e) or re.search(r"nsfw|erotic|uncensor|nude|porn|hentai|lewd", r["id"], re.I):
            continue
        out.append(r)
    return out


def run(r):
    sid = r["id"]
    d = OUT / sid.replace("/", "__")
    d.mkdir(exist_ok=True)
    meta = {}
    try:
        repo = sandbox.SPACES_ROOT / sid.replace("/", "__") / "orig"
        sandbox.fetch_space(sid, repo)
        readme = repo / "README.md"
        meta = sandbox.front_matter(readme.read_text(errors="replace")) if readme.exists() else {}
        meta["_python"] = sandbox.python_for(meta, r["err"])
        res = sandbox.build_and_test(repo, meta, tag="sd-orig-" + re.sub(r"[^a-z0-9]", "-", sid.lower())[:50], boot_timeout=600)
    except Exception as e:
        res = {"stage": "harness_error", "logs": repr(e)}
    hf_exc, our_exc = last_exc(r["err"]), last_exc(res.get("logs", ""))
    rec = {"space": sid, "likes": r["likes"], "meta": {k: v for k, v in meta.items() if k in ("sdk", "sdk_version", "python_version", "app_file", "_python")},
           "hf_error_tail": r["err"][-4000:], "hf_exception": hf_exc, "our_stage": res["stage"],
           "our_exception": our_exc, "same_exception": bool(hf_exc) and hf_exc.split(":")[0] == our_exc.split(":")[0],
           "our_logs": res.get("logs", ""), "api": res.get("api"), "secs": res.get("secs"), "freeze": res.get("freeze", "")}
    json.dump(rec, open(d / "repro.json", "w"), indent=1)
    print(f"{sid:60s} {res['stage']:14s} same={rec['same_exception']} | {our_exc[:100]}", flush=True)
    return rec


if __name__ == "__main__":
    cs = candidates()
    print(f"{len(cs)} code-level candidates; reproducing top {N}", flush=True)
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(run, [r for r in cs[:N] if not (OUT / r["id"].replace("/", "__") / "repro.json").exists()]))
