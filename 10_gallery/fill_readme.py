"""Render README.md for the Space from README_TEMPLATE.md using only final/summary.json and final/repro/*/case.json.
usage: fill_readme.py FINAL_DIR OUT_README [--authors "..."] [--video URL] [--hf-user NAME]"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import argparse, json, re
from pathlib import Path
from string import Template

ap = argparse.ArgumentParser()
ap.add_argument("final"); ap.add_argument("out")
ap.add_argument("--authors", default="[Kavya Bhand](https://huggingface.co/kavyabhand) & [Aadi Joshi](https://huggingface.co/aadi-joshi)")
ap.add_argument("--video", default="")
ap.add_argument("--hf-user", default="kavyabhand")
a = ap.parse_args()
F = Path(a.final)
S = json.load(open(F / "summary.json"))
cases = [json.load(open(d / "case.json")) for d in sorted((F / "repro").iterdir()) if (d / "case.json").exists()]
_rv = _ROOT / "06_verify_and_review" / "reviews.json"
_reviews = json.load(open(_rv)) if _rv.exists() else {}
for x in cases:
    v = _reviews.get(x["space"], {}).get("verdict")
    if v == "rejected":
        x["tier"] = "rejected"
    elif v == "unverified" and x.get("tier") == "functional":
        x["tier"] = "api"
repros = [json.load(open(d / "repro.json")) for d in sorted((F / "repro").iterdir()) if (d / "repro.json").exists()]
c, r, t, b, T = S["census"], S["reproduction"], S["treatment"], S["baseline"], S.get("triage", {})
fmt = lambda n: f"{n:,}"
pct = lambda x: f"{round(100 * x)}%"
tiers = t["tiers"]
revived = [x for x in cases if x.get("tier") == "functional"]
best = lambda x: next(a for a in x["attempts"] if a["stage"] == "functional")

def short(e, n=64):
    e = e.replace("|", "/")
    return e if len(e) <= n else e[:n].rsplit(" ", 1)[0] + " …"


rows = ["| Space | Likes | Hardware | What was wrong | Fix |", "|---|---|---|---|---|"]
for x in sorted(revived, key=lambda x: -x["likes"])[:12]:
    at = best(x)
    files = sorted(set(l[6:] for l in at["diff"].splitlines() if l.startswith("+++ b/")))
    fix = ("lockfile as of " + at["lock"]["date"] + " + " if at.get("lock") else "") + ", ".join(f"`{f}`" for f in files)
    rows.append(f"| [{x['space']}](https://huggingface.co/spaces/{x['space']}) | {x['likes']} | {'A10G' if x.get('gpu') else 'CPU'} | "
                f"`{short(x['hf_exception'])}` | {fix} |")
highlights = "\n".join(rows) if revived else "_Revivals are listed in the gallery._"

calls = [k for x in cases for k in x["calls"]]
empty = sum(1 for k in calls if k.get("empty_retry"))
bad = sum(1 for x in cases for a in x["attempts"] for tt in a.get("turns", []) if "apply_error" in tt) + \
      sum(1 for x in cases for a in x["attempts"] if a["stage"] == "bad_edit")
PRS = _ROOT / "08_results" / "prs.json"
PRD = json.load(open(PRS)) if PRS.exists() else {}
prs = list(PRD.values())
likes = {x["space"]: x["likes"] for x in cases}
fixed_at = ", ".join(f"{v} revived at {k}" for k, v in sorted(t["fixed_at"].items(), key=lambda kv: -kv[1])) or "-"
tri_calls = len(T.get("prompt_tokens") or [])
cmp_n = b["beam_only"] + b["baseline_only"] + b["both"] + b["neither"]
if cmp_n:
    note = (f"On the {cmp_n} patients run both ways, Beam revived {b['beam_only'] + b['both']} and the baseline "
            f"{b['baseline_only'] + b['both']}. ")
    bo = b["baseline_only"]
    note += (f"The baseline revived {bo} Space{'s' if bo != 1 else ''} that Beam did not; the case files show {'them' if bo != 1 else 'it'} rather than hide {'them' if bo != 1 else 'it'}."
             if bo else "There was no Space the baseline revived that Beam did not.")
else:
    note = "_Baseline comparison pending._"

_G = Path(__file__).parent / "data" / "summary.json"
_E = (json.load(open(_G)).get("efficiency") or {}) if _G.exists() else {}
_n = lambda v: fmt(round(v)) if v is not None else "-"
vals = dict(
    median_reasoning=_n(_E.get("median_reasoning_per_call")), out_per_revived_median=_n(_E.get("median_output_per_revived")),
    triage_reasoning=_n(_E.get("triage_reasoning")),
    authors=a.authors, hf_user=a.hf_user,
    video_url=a.video or "#", video_md=f"[Watch]({a.video})" if a.video else "In the Space header",
    census_date=c["date"], spaces=fmt(c["spaces"]), broken=fmt(c["broken"]), broken_pct=pct(c["broken"] / c["spaces"]),
    broken_likes=fmt(c["broken_likes"]), repro_attempted=fmt(r["attempted"]), still_broken=fmt(r["still_broken"]),
    same_exc=fmt(r["same_exception_as_hf"]), transient=fmt(r["attempted"] - r["still_broken"]),
    treated=fmt(t["treated"]), gpu_cases=fmt(t["gpu_cases"]), revived=fmt(tiers.get("functional", 0)),
    likes_revived=fmt(t["likes_revived"]), api_tier=fmt(tiers.get("api", 0)), unfixable=fmt(tiers.get("unfixable", 0)),
    failed=fmt(tiers.get("failed", 0)), highlights=highlights, guard=fmt(t["guard_rejections"]),
    triage_logs=fmt(T.get("n_logs", 0)), triage_tokens=fmt((T.get("prompt_tokens") or [0])[0]),
    triage_secs=round((T.get("secs") or [0])[0]) if isinstance(T.get("secs"), list) else T.get("secs"),
    catch_all=fmt(sum(f["matched"] for f in T.get("catch_all_families", []))),
    cov_reported=pct(T.get("coverage_reported", 0)), cov_specific=pct(T.get("coverage_specific", 0)),
    lock_used=fmt(sum(1 for x in revived if best(x).get("lock"))), fixed_at=fixed_at,
    beam_only=fmt(b["beam_only"]), baseline_only=fmt(b["baseline_only"]), both=fmt(b["both"]), neither=fmt(b["neither"]),
    baseline_note=note, bad_edits=fmt(bad), empty=fmt(empty),
    rejected=fmt(tiers.get("rejected", 0)),
    unverified_rev=fmt(sum(1 for v in _reviews.values() if v.get("verdict") == "unverified")),
    guard_line=(f"**The integrity guard rejected {fmt(t['guard_rejections'])} patch{'es' if t['guard_rejections'] != 1 else ''}** that would have made a Space boot by removing what it does."
                if t["guard_rejections"] else "**The integrity guard never had to fire** in the final run: no patch tried to boot a Space by deleting code or swallowing its errors."),
    empty_line=(f"- **Empty answers.** {fmt(empty)} times Beam reasoned, then returned no content. We retry once and count it.\n" if empty else ""),
    calls=fmt(t["beam_calls"] + tri_calls), prompt_tokens=fmt(t["prompt_tokens"] + sum(T.get("prompt_tokens") or [])),
    cached_pct=pct(t["cached_prompt_tokens"] / max(1, t["prompt_tokens"])), completion_tokens=fmt(t["completion_tokens"]),
    out_per_revival=fmt(round(t["completion_tokens"] / max(1, tiers.get("functional", 0)))),
    median_call=round(t["median_beam_secs"] or 0), median_wall=round((t["median_wall_secs"] or 0) / 60),
    n_prs=len(prs),
    authors_html=re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', a.authors).replace("&", "&amp;"),
    prs_table=("| Space | Likes | Pull request |\n|---|---|---|\n" + "\n".join(
        f"| [{k}](https://huggingface.co/spaces/{k}) | {likes.get(k, '')} | [#{v.rsplit('/', 1)[1]}]({v}) |"
        for k, v in sorted(PRD.items(), key=lambda kv: -likes.get(kv[0], 0)))) if prs else "_None yet._",
    prs_md=(f"{len(prs)} opened on revived Spaces, each with its evidence: " + ", ".join(f"[{p.split('/spaces/')[1].split('/discussions')[0]}]({p})" for p in prs))
           if prs else "Opened only for verified revivals, after human review",
)
text = Template((Path(__file__).parent / "README_TEMPLATE.md").read_text()).substitute(vals)

# Re-align the two-column ASCII pipeline after numbers are substituted.
def _align(block, col=40):
    out = []
    for ln in block.splitlines():
        m = re.match(r"^(\S.*?|\s+\|)\s{2,}(\S.*)$", ln)
        out.append(m.group(1).ljust(col) + m.group(2) if m else ln)
    return "\n".join(out)
_i = text.find("```\n", text.find("## What It Does")) + 4
_j = text.find("```", _i)
text = text[:_i] + _align(text[_i:_j].rstrip("\n")) + "\n" + text[_j:]
Path(a.out).write_text(text)
print(f"wrote {a.out}: {len(text):,} chars, {tiers.get('functional', 0)} revived")
