"""Write the gallery's data files: data/summary.json, data/triage.json, data/cases.json, data/outputs/<space>/*.
usage: export_gallery.py DATA_DIR OUT_DIR"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, re, shutil, sys
from pathlib import Path

REDACT = [  # credential-shaped strings that appear inside third-party error logs (e.g. expired pre-signed URLs)
    (re.compile(r"(X-Amz-(?:Credential|Signature|Security-Token)(?:=|%3D|%253D))[^&%\s\"']+(?:%2F[^&\s\"']*)?"), r"\1[REDACTED]"),
    (re.compile(r"(sign(?:ature)?=)eyJ[A-Za-z0-9._-]+"), r"\1[REDACTED]"),
    (re.compile(r"eyJhbGci" r"Oi[A-Za-z0-9._-]+"), "[REDACTED_JWT]"),
    (re.compile(r"hf_[A-Za-z0-9]{30,}"), "hf_[REDACTED]"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "sk-[REDACTED]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA[REDACTED]"),
]


def redact(text):
    for rx, rep in REDACT:
        text = rx.sub(rep, text)
    return text


D = Path(sys.argv[1] if len(sys.argv) > 1 else "/data")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "/data/gallery/data")
out.mkdir(parents=True, exist_ok=True)
shutil.rmtree(out / "outputs", ignore_errors=True)  # only current revivals' outputs, never stale ones
json.dump(json.load(open(D / "summary.json")), open(out / "summary.json", "w"))
if (D / "triage.json").exists():
    t = json.load(open(D / "triage.json"))
    t.pop("assignment", None)  # the per-Space mapping lives in the dataset, not the page
    (out / "triage.json").write_text(redact(json.dumps(t)))

REV = json.load(open(_ROOT / "06_verify_and_review" / "reviews.json")) if (_ROOT / "06_verify_and_review" / "reviews.json").exists() else {}
PRS = json.load(open(_ROOT / "08_results" / "prs.json")) if (_ROOT / "08_results" / "prs.json").exists() else {}
# Compact census for the field figure: [id, likes, stage code] sorted by likes. 0 running, 1 idle, 2 broken.
CODE = {"RUNTIME_ERROR": 2, "BUILD_ERROR": 2, "CONFIG_ERROR": 2, "PAUSED": 1, "SLEEPING": 1}
cen = sorted(json.load(open(D / "census.json")), key=lambda r: -r["likes"])
json.dump([[r["id"], r["likes"], CODE.get(r["stage"], 0)] for r in cen], open(out / "census_min.json", "w"), separators=(",", ":"))
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".wav", ".mp3", ".flac", ".ogg", ".mp4", ".webm"}
cases = []
for d in sorted((D / "repro").iterdir()):
    if not (d / "case.json").exists():
        continue
    c = json.load(open(d / "case.json"))
    rec = json.load(open(d / "repro.json"))
    if c.get("hidden"):
        continue
    last = c["attempts"][-1] if c["attempts"] else {}
    best = next((a for a in c["attempts"] if a["stage"] == c.get("tier")), last)
    status = c.get("tier") or ("unfixable" if last.get("stage") == "declared_unfixable" else "failed")
    review = REV.get(c["space"])
    if review and review.get("verdict") == "rejected":
        status = "rejected"
    elif review and review.get("verdict") == "unverified" and status == "functional":
        status = "api"
    probe = next((p for p in (best.get("probe") or []) if p.get("ok") and not p.get("helper")), None)
    media = []
    if status == "functional" and (d / "outputs").exists():
        dst = out / "outputs" / d.name
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted((d / "outputs").iterdir())[:4]:
            if f.suffix.lower() in MEDIA and f.stat().st_size < 4_000_000:
                safe = f.name.replace(":", "_")
                shutil.copy(f, dst / safe)
                media.append(f"data/outputs/{d.name}/{safe}")
    b = json.load(open(d / "baseline.json")) if (d / "baseline.json").exists() else None
    cases.append({
        "space": c["space"], "likes": c["likes"], "gpu": bool(c.get("gpu")), "status": status, "sdk": (rec.get("meta") or {}).get("sdk"),
        "hf_exception": c["hf_exception"], "hf_error_tail": rec.get("hf_error_tail", "")[-1500:],
        "same_exception": bool(rec.get("same_exception")),
        "diagnosis": best.get("diagnosis", ""), "category": best.get("category"),
        "diff": best.get("diff", "") if c.get("tier") else "",
        "review": review, "reprobed": bool(c.get("reprobe", {}).get("functional")),
        "probe": ({"endpoint": probe["endpoint"], "inputs": probe["inputs"], "output": probe["output_summary"]} if probe else None),
        "media": media, "baseline": (b or {}).get("tier"),
        "tokens": c["tokens"], "wall_secs": c["wall_secs"],
        "apply_errors": sum(1 for a in c["attempts"] for t in a.get("turns", []) if "apply_error" in t),
        "need_files": sum(1 for a in c["attempts"] for t in a.get("turns", []) if "need_files" in t),
        "empty_retries": sum(1 for k in c["calls"] if k.get("empty_retry")),
        "lock": next((a.get("lock") for a in c["attempts"] if a["stage"] == c.get("tier")), None),
        "attempts": [{"effort": a["effort"], "stage": a["stage"], "diagnosis": a.get("diagnosis", "")[:600],
                      "guard": a["logs"] if a["stage"] == "rejected_by_integrity_guard" else ""} for a in c["attempts"]],
        "pr": PRS.get(c["space"]),
    })
order = {"functional": 0, "api": 1, "rejected": 2, "unfixable": 3, "failed": 4}
cases.sort(key=lambda c: (order[c["status"]], -c["likes"]))
(out / "cases.json").write_text(redact(json.dumps(cases)))
print(f"{len(cases)} cases -> {out}")
