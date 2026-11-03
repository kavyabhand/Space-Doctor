"""Open a pull request on a revived Space with exactly the files Beam changed, plus the evidence.
usage: open_pr.py CASE_DIR [--go]      (without --go it only prints what it would send)
Refuses unless the case reached the 'functional' tier and its diff only touches files present in fixed/."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, re, sys
from pathlib import Path

from huggingface_hub import CommitOperationAdd, HfApi

d = Path(sys.argv[1])
go = "--go" in sys.argv
case = json.load(open(d / "case.json"))
rec = json.load(open(d / "repro.json"))
assert case.get("tier") == "functional", f"{case['space']}: not functional ({case.get('tier')}), refusing"
_rv = _ROOT / "06_verify_and_review" / "reviews.json"
_review = (json.load(open(_rv)) if _rv.exists() else {}).get(case["space"])
assert _review and _review.get("verdict") == "approved", f"{case['space']}: no approved review in reviews.json, refusing"
assert _review.get("pr", True), f"{case['space']}: review says no PR ({_review['reason'][:80]})"
best = next(a for a in case["attempts"] if a["stage"] == "functional")
paths = re.findall(r"^\+\+\+ b/(.+)$", best["diff"], re.M)
assert paths, "empty diff"
for p in paths:
    assert (d / "fixed" / p).is_file(), f"missing fixed/{p}"
probe = next(p for p in best["probe"] if p.get("ok") and not p.get("helper"))
hw = "an NVIDIA A10G (same GPU as a10g-small)" if case.get("gpu") else "2 vCPU / 16 GB, like cpu-basic"
lock = best.get("lock")
out = probe["output_summary"]
if probe.get("files"):  # gradio_client returns local temp paths for media; say what came back instead
    kinds = sorted({Path(f).suffix.lstrip(".").lower() for f in probe["files"]})
    out = f"{len(probe['files'])} output file(s) ({', '.join(kinds)}), non-empty"
out = out if len(out) < 300 else out[:300] + " …"

exc_type = rec["hf_exception"].split(":")[0].strip()[:60] or "startup error"
title = f"Fix startup crash: {exc_type} ({best.get('category') or 'dependency drift'})"
pin_note = " `python_version` is pinned in the README to the interpreter we tested with." if "+python_version:" in best["diff"] else ""
body = f"""Hi! This Space currently fails to start on Hugging Face with:

```
{rec['hf_exception']}
```

**Cause.** {best['diagnosis']}

**Change.** {', '.join(f'`{p}`' for p in paths)}.{f" `requirements.txt` is a lockfile resolved as of {lock['date']} (Python {lock['python']}), so the app runs on the library versions it was written for." if lock else ""}{pin_note} Nothing else is touched.

**Tested.** We rebuilt the Space with this patch the way Spaces builds it (README front-matter, `requirements.txt`, then the SDK), on {hw}. The app started, and calling its `{probe['endpoint']}` endpoint returned:

```
{out}
```

The diagnosis and patch were written by [Beam](https://huggingface.co/reflection/Beam-1.0-501B-A23B) (Reflection AI's open model) as part of Space Doctor, a Build with Beam challenge project that repairs broken Spaces and only proposes fixes that pass this check. We read the diff before opening this PR. Feel free to close it if you'd rather fix it another way.
"""
print(f"== {case['space']}\nTITLE: {title}\nFILES: {paths}\n{body}")
PRS = _ROOT / "08_results" / "prs.json"
prs = json.load(open(PRS)) if PRS.exists() else {}
assert case["space"] not in prs, f"PR already opened: {prs.get(case['space'])}"
stage = HfApi().get_space_runtime(case["space"]).stage
print("current stage on Hugging Face:", stage)
assert stage in ("RUNTIME_ERROR", "BUILD_ERROR", "CONFIG_ERROR"), "Space is not broken any more; not opening a PR"
if go:
    ops = [CommitOperationAdd(path_in_repo=p, path_or_fileobj=str(d / "fixed" / p)) for p in paths]
    info = HfApi().create_commit(repo_id=case["space"], repo_type="space", operations=ops, create_pr=True,
                                 commit_message=title, commit_description=body)
    prs[case["space"]] = info.pr_url
    json.dump(prs, open(PRS, "w"), indent=1)
    print("OPENED", info.pr_url)
