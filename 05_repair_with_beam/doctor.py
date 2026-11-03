"""Space Doctor: Beam reads a broken Space whole, proposes a minimal patch, and we rebuild until it boots.

Loop per Space (only for Spaces whose failure we reproduced):
  1. Context = README front-matter + every text file in the repo + Hugging Face's public error log
     + our reproduction log + the exact package versions the failing build resolved + migration notes.
  2. Beam returns a JSON patch (diagnosis + edits). Effort escalates medium -> high -> xhigh on failure.
  3. Integrity guard rejects patches that "fix" a Space by gutting it (Beam is known to take shortcuts).
  4. Rebuild with the Spaces recipe; success = boots, serves HTTP 200, and exposes its API to gradio_client.
"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import difflib, json, os, re, shutil, sys, threading, time
from pathlib import Path

import beam, sandbox

NOTES = (Path(__file__).parent / "migration_notes.md").read_text()
EFFORTS = ["medium", "medium", "high"]  # high only on the last try: it costs ~4x the output tokens
MAX_TOKENS = {"low": 12000, "medium": 16000, "high": 32000, "xhigh": 48000}
LOCK_TOOL = os.environ.get("SD_LOCK", "1") == "1"  # pass 2: Beam may also ask for a dated lockfile
STOP = threading.Event()  # set when the daily Beam budget is reached; untreated Spaces stay queued for tomorrow
NSFW = re.compile(r"nsfw|erotic|uncensor|nude|porn|hentai|lewd", re.I)  # not treated or showcased

SYSTEM = """You are Space Doctor. You repair broken Hugging Face Spaces so they run again on today's Spaces platform.

Rules:
- Find the root cause from the logs. Do not guess past evidence; cite the log line that proves it.
- Make the smallest change that makes the Space run with its original functionality intact.
- Never stub out, delete, or bypass the app's features, model loading, or inference to make it boot.
  Never wrap imports in try/except to hide failures. If the Space cannot be fixed honestly (needs a GPU,
  a paid API key, a deleted model, a dead external service), say so with "verdict": "unfixable".
- The rebuild has no secrets. If the app only works with the owner's secret (e.g. a 401 on a private model repo,
  or an API key it cannot run without), the verdict is "unfixable", even if you also see a code bug; mention
  that bug in the diagnosis so the owner can fix it.
- Prefer pinning versions in requirements.txt or bumping sdk_version in README.md front-matter when that is
  the honest fix; edit code when the API it uses no longer exists.
- Keep README.md front-matter valid YAML.
- Only edit files whose content you have been shown. If you need a file listed under NOT SHOWN, ask for it
  first with {"need_files": ["path", ...]} instead of a patch; never guess a file's contents.

Respond with ONE JSON object and nothing else:
{"diagnosis": "<root cause in 1-3 sentences, quoting the decisive log line>",
 "category": "<short label, e.g. gradio-api-drift, hf-hub-api-removed, numpy2-abi, py313-stdlib-removal, dependency-conflict>",
 "verdict": "fixable" | "unfixable",
 "edits": [{"path": "<repo-relative path>", "search": "<exact existing text>", "replace": "<new text>"}
           | {"path": "<repo-relative path>", "content": "<full new file content>"}],
 "expected_effect": "<what should happen on rebuild>"}
Use search/replace for code files (search must match exactly once). Use full content only for small files."""


LOCK_HELP = """
Tool: dependency lock. Besides edits, you may return
 "lock": {"date": "YYYY-MM-DD", "python": "3.10"}
and we will resolve requirements.txt (plus the README's gradio/streamlit sdk_version) with
`uv pip compile --exclude-newer <date> --python-version <python>` and replace requirements.txt with the fully pinned
result, and set python_version in README.md. Use it when the code is from an older era and chasing one broken pin
at a time will not converge (e.g. old gradio 3.x stacks); pick a date when the code's own pins existed. You can
combine it with code edits, and you may bump sdk_version in README.md if needed. Do not use it when a small code
edit keeps the Space on today's libraries."""


def lock_requirements(repo: Path, date: str, python: str, meta: dict) -> str:
    """Write a fully pinned requirements.txt resolved as of `date`. Returns the uv output tail."""
    req = repo / "requirements.txt"
    src = repo / ".sd_lock_in.txt"
    lines = req.read_text(errors="replace").splitlines() if req.exists() else []
    sdk, ver = meta.get("sdk"), meta.get("sdk_version")
    if sdk in ("gradio", "streamlit") and ver:  # Spaces installs the SDK after requirements.txt, so the SDK pin wins
        lines = [l for l in lines if not re.match(rf"\s*{sdk}\b(?![-_])", l, re.I)]
    if sdk == "gradio" and ver:
        lines.append(f"gradio[oauth]=={ver}")
    elif sdk == "streamlit" and ver:
        lines.append(f"streamlit=={ver}")
    src.write_text("\n".join(l for l in lines if l.strip() and not l.strip().startswith(("-", "#"))) + "\n")
    rc, out = sandbox.sh([str(Path(sys.executable).with_name("uv")), "pip", "compile", str(src), "--exclude-newer",
                          f"{date}T23:59:59Z", "--python-version", python, "--python-platform", "x86_64-manylinux_2_28",
                          "--no-header", "--no-annotate", "-o", str(req)], timeout=600)
    src.unlink()
    if rc != 0:
        raise ValueError(f"lock failed: {out[-1500:]}")
    return out[-500:]


def build_prompt(rec, repo_text, freeze, attempts, recipe=""):
    parts = [f"# Space: {rec['space']} ({rec['likes']} likes)",
             f"## Hugging Face's own error log (tail)\n```\n{rec['hf_error_tail'][-5000:]}\n```",
             f"## Our rebuild of the original, same recipe as Spaces (stage: {rec['our_stage']})\n```\n{rec['our_logs'][-5000:]}\n```"]
    if freeze:
        parts.append(f"## Packages the failing build resolved (pip freeze)\n```\n{freeze[:6000]}\n```")
    if recipe:
        parts.append("## How the Space is built (this Dockerfile is generated from README.md front-matter and the repo; "
                     "note that the SDK and `spaces` are installed AFTER requirements.txt and can upgrade what it pins)\n"
                     f"```dockerfile\n{recipe}```")
    parts.append(f"## Migration notes (hints, verify against the logs)\n{NOTES}")
    parts.append(f"## Repository (every text file)\n{repo_text}")
    for i, a in enumerate(attempts, 1):
        parts.append(f"## Previous attempt {i} (did not work)\nDiagnosis: {a['diagnosis']}\nDiff:\n```diff\n{a['diff'][:6000]}\n```\n"
                     f"Rebuild result: {a['stage']}\n```\n{a['logs'][-4000:]}\n```")
    if LOCK_TOOL:
        parts.append(LOCK_HELP)
    parts.append("Return the JSON object now.")
    return "\n\n".join(parts)


def parse_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    return json.loads(text[start:end + 1])


def apply_edits(repo: Path, edits):
    for e in edits:
        p = (repo / e["path"]).resolve()
        if repo.resolve() not in p.parents:
            raise ValueError(f"edit escapes repo: {e['path']}")
        if "content" in e:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(e["content"])
        else:
            with open(p, encoding="utf-8", errors="replace", newline="") as f:  # keep the file's own line endings
                s = f.read()
            start, length = _locate(s, e["search"], e["path"])
            rep = e["replace"].replace("\n", "\r\n") if "\r\n" in s and "\r\n" not in e["replace"] else e["replace"]
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(s[:start] + rep + s[start + length:])


def _locate(s, search, path):
    """Exact match first; else tolerate CRLF and trailing whitespace. Must be unique either way."""
    n = s.count(search)
    if n == 1:
        return s.index(search), len(search)
    if n == 0 and search.strip():
        pat = r"\r?\n".join(re.escape(l.rstrip()) + r"[ \t]*" for l in search.rstrip("\n").split("\n"))
        ms = list(re.finditer(pat, s))
        if len(ms) == 1:
            return ms[0].start(), ms[0].end() - ms[0].start()
        n = len(ms)
    raise ValueError(f"search text found {n} times in {path}" + (" (add surrounding lines to make it unique)" if n > 1 else
                     " (quote the file's exact current lines, in order)"))


def repo_diff(a: Path, b: Path) -> str:
    out = []
    for pb in sorted(b.rglob("*")):
        if not pb.is_file() or pb.name == "Dockerfile.spacedoctor" or pb.suffix.lower() not in sandbox.TEXT_EXT | {""}:
            continue
        rel = pb.relative_to(b)
        pa = a / rel
        ta = pa.read_text(errors="replace").splitlines() if pa.exists() else []
        tb = pb.read_text(errors="replace").splitlines()
        if ta != tb:
            out += [l + "\n" for l in difflib.unified_diff(ta, tb, f"a/{rel.as_posix()}", f"b/{rel.as_posix()}", lineterm="")]
    return "".join(out)


def _py_stats(root: Path):
    lines, defs = 0, set()
    for f in root.rglob("*.py"):
        if ".git" in f.parts:
            continue
        t = f.read_text(errors="replace")
        lines += sum(1 for l in t.splitlines() if l.strip())
        defs |= {f"{f.relative_to(root).as_posix()}:{d}" for d in re.findall(r"^\s*def (\w+)", t, re.M)}
    return lines, defs


def integrity(orig: Path, fixed: Path, meta) -> list:
    """Flags patches that make a Space 'boot' by removing what it does (checked across every .py file)."""
    problems = []
    la, da = _py_stats(orig)
    lb, db = _py_stats(fixed)
    if la and lb < 0.85 * la:
        problems.append(f"Python code shrank from {la} to {lb} non-blank lines")
    if da - db:
        problems.append(f"functions removed: {sorted(da - db)[:8]}")
    # Special-token text such as <|endoftext|> cannot be written back reliably by the model (it can come out as
    # junk); a patch that changes how often such text appears silently corrupts the app.
    tok = re.compile(r"<\|[A-Za-z0-9_]+\|>")
    def _toks(root):
        n = 0
        for f in root.rglob("*.py"):
            if ".git" not in f.parts:
                n += len(tok.findall(f.read_text(errors="replace")))
        return n
    if _toks(orig) != _toks(fixed):
        problems.append("special-token text like <|endoftext|> was changed; leave lines containing such tokens untouched "
                        "and edit around them")
    app = meta.get("app_file", "app.py")
    a, b = orig / app, fixed / app
    if a.exists() and b.exists():
        la = [l for l in a.read_text(errors="replace").splitlines() if l.strip()]
        lb = [l for l in b.read_text(errors="replace").splitlines() if l.strip()]
        if len(lb) < 0.7 * len(la):
            problems.append(f"{app} shrank from {len(la)} to {len(lb)} non-blank lines")
        ea = sum(1 for l in la if re.match(r"\s*except\b", l))
        eb = sum(1 for l in lb if re.match(r"\s*except\b", l))
        if eb > ea + 1:
            problems.append(f"{eb - ea} new except-clauses in {app}")
        defs_a = set(re.findall(r"^\s*def (\w+)", a.read_text(errors="replace"), re.M))
        defs_b = set(re.findall(r"^\s*def (\w+)", b.read_text(errors="replace"), re.M))
        if defs_a - defs_b:
            problems.append(f"functions removed: {sorted(defs_a - defs_b)}")
    elif a.exists() and not b.exists():
        problems.append(f"{app} deleted")
    rm = fixed / "README.md"
    if rm.exists():
        fm = sandbox.front_matter(rm.read_text(errors="replace"))
        if fm.get("sdk") != meta.get("sdk"):
            problems.append(f"sdk changed {meta.get('sdk')} -> {fm.get('sdk')}")
    return problems


def treat(space_dir: Path, max_attempts=3):
    rec = json.load(open(space_dir / "repro.json"))
    sid = rec["space"]
    orig = sandbox.SPACES_ROOT / sid.replace("/", "__") / "orig"
    sandbox.fetch_space(sid, orig)  # full snapshot (examples, small weights) so a correct fix is not failed by missing files
    meta = dict(sandbox.front_matter((orig / "README.md").read_text(errors="replace")))
    meta["_python"] = rec["meta"].get("_python")
    freeze = rec.get("freeze", "")
    tag_orig = "sd-orig-" + re.sub(r"[^a-z0-9]", "-", sid.lower())[:50]
    try:
        rc, out = (1, "") if freeze else sandbox.sh(["docker", "run", "--rm", "--entrypoint", "pip", tag_orig, "freeze"], timeout=300)
        if rc == 0:
            freeze = out
    except Exception:
        pass
    attempts, calls, saved_rank = [], [], 0
    t_start = time.time()
    for k in range(max_attempts):
        effort = EFFORTS[min(k, len(EFFORTS) - 1)]
        fixed = orig.parent / "fixed"
        if STOP.is_set():
            raise beam.BudgetExhausted("stop flag set")
        recipe = sandbox.dockerfile_for(meta, orig)
        first = {meta.get("app_file", "app.py")} | {m for m in re.findall(r"/home/user/app/([\w./-]+\.py)", rec["hf_error_tail"] + rec["our_logs"])}
        prompt = build_prompt(rec, sandbox.repo_text(orig, first=first), freeze, attempts, recipe)
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
        att = {"effort": effort, "turns": []}
        stage = None
        # Inner loop, no rebuild: Beam may ask for files it was not shown, and a patch that does not apply or a lock
        # that does not resolve goes straight back to it. Only a patch that applies cleanly gets rebuilt.
        for turn in range(3):
            r = beam.chat(msgs, effort=effort, max_tokens=MAX_TOKENS[effort], tag=sid)
            if not r["content"].strip() and r["finish_reason"] == "stop":  # Beam occasionally reasons, then answers nothing
                calls.append({k: r[k] for k in ("usage", "finish_reason", "secs", "effort")} | {"empty_retry": True})
                r = beam.chat(msgs, effort=effort, max_tokens=MAX_TOKENS[effort], tag=sid)
            calls.append({k: r[k] for k in ("usage", "finish_reason", "secs", "effort")})
            att.update(raw=r["content"], reasoning=r["reasoning"], usage=r["usage"])
            if r["finish_reason"] == "length":
                att.update(diagnosis="(ran out of output tokens before answering)", diff="", logs="")
                stage = "truncated"
                break
            feedback = None
            try:
                plan = parse_json(r["content"])
            except Exception as e:
                plan, feedback = None, f"Your answer was not one valid JSON object ({e}). Return the JSON object only."
            if plan is not None and plan.get("need_files"):
                att["turns"].append({"need_files": plan["need_files"][:12]})
                feedback = "Here are the files you asked for:" + sandbox.read_files(orig, list(plan["need_files"])) + \
                           "\n\nNow return the JSON patch object."
            elif plan is not None:
                att.update(diagnosis=plan.get("diagnosis", ""), category=plan.get("category"), verdict=plan.get("verdict"))
                if plan.get("verdict") == "unfixable":
                    att.update(diff="", logs="")
                    stage = "declared_unfixable"
                    break
                if fixed.exists():
                    shutil.rmtree(fixed)
                shutil.copytree(orig, fixed, ignore=shutil.ignore_patterns("Dockerfile.spacedoctor"))
                try:
                    apply_edits(fixed, plan.get("edits", []))
                    att.pop("lock", None)
                    if LOCK_TOOL and isinstance(plan.get("lock"), dict) and plan["lock"].get("date"):
                        lk = plan["lock"]
                        py = str(lk.get("python") or meta.get("_python") or "3.10")
                        fm0 = sandbox.front_matter((fixed / "README.md").read_text(errors="replace"))
                        lock_requirements(fixed, str(lk["date"])[:10], py, fm0)
                        rd = fixed / "README.md"
                        t = rd.read_text(errors="replace")
                        t = re.sub(r'^python_version:.*\n', "", t, count=1, flags=re.M)
                        rd.write_text(re.sub(r"^---\s*\n", f'---\npython_version: "{py}"\n', t, count=1))
                        att["lock"] = {"date": str(lk["date"])[:10], "python": py}
                    break  # patch applies: go rebuild
                except Exception as e:
                    att["turns"].append({"apply_error": str(e)[:1500]})
                    feedback = f"Your patch could not be applied: {str(e)[:1500]}\nFix it and return the complete JSON object again."
            msgs += [{"role": "assistant", "content": r["content"], "reasoning_content": r["reasoning"]},
                     {"role": "user", "content": feedback}]
        else:
            att.update(diagnosis=att.get("diagnosis") or "(no applicable patch after 3 turns)", diff="",
                       logs=json.dumps(att["turns"])[-1500:])
            stage = "bad_edit"
        if stage:
            att["stage"] = stage
            attempts.append(att)
            if stage == "declared_unfixable":
                break
            continue
        att["diff"] = repo_diff(orig, fixed)
        problems = integrity(orig, fixed, meta)
        if problems:
            att.update(stage="rejected_by_integrity_guard", logs="; ".join(problems))
            attempts.append(att)
            continue
        fm = sandbox.front_matter((fixed / "README.md").read_text(errors="replace"))
        if not fm.get("python_version"):
            # Spaces' default interpreter has moved over time; pin the one we verify with so the fix is reproducible.
            rd = fixed / "README.md"
            rd.write_text(re.sub(r"^---\s*\n", f'---\npython_version: "{meta["_python"]}"\n', rd.read_text(errors="replace"), count=1))
            att["diff"] = repo_diff(orig, fixed)
            fm = sandbox.front_matter(rd.read_text(errors="replace"))
        fmeta = dict(fm, _python=fm.get("python_version") or meta["_python"])
        outs = orig.parent / f"outputs_{k}"
        shutil.rmtree(outs, ignore_errors=True)
        tag = "sd-fix-" + re.sub(r"[^a-z0-9]", "-", sid.lower())[:50]
        res = sandbox.build_and_test(fixed, fmeta, tag=tag, outdir=outs)
        if res["stage"] in ("runtime_error", "boot_timeout") and re.search(r"\b429\b|Too Many Requests", res.get("logs", "")):
            time.sleep(90)  # Hub rate limit on our side: re-run the same build once; not Beam's failure
            res = sandbox.build_and_test(fixed, fmeta, tag=tag, outdir=outs)
            att["rate_limit_retry"] = True
        api_ok = res["stage"] == "running" and (fmeta.get("sdk") != "gradio" or not str(res.get("api", "")).startswith("API_ERROR"))
        # Tiers: boots < api (client can read its schema) < functional (an endpoint returned a result).
        functional = api_ok and (fmeta.get("sdk") not in ("gradio", "streamlit") or res.get("functional"))
        stage = res["stage"] if res["stage"] != "running" else ("functional" if functional else "api" if api_ok else "api_error")
        probe_log = "\n".join(json.dumps(p) for p in res.get("probe", []))
        att.update(stage=stage, logs=(f"PROBE (we called the app's endpoints with synthetic inputs):\n{probe_log}\n\nAPP LOG:\n" if probe_log else "") + res.get("logs", ""),
                   api=res.get("api"), probe=res.get("probe"))
        attempts.append(att)
        rank = {"functional": 2, "api": 1}.get(stage, 0)
        if rank > saved_rank:  # keep the best verified patch, not merely the last one
            if (space_dir / "fixed").exists():
                shutil.rmtree(space_dir / "fixed")
            shutil.copytree(fixed, space_dir / "fixed", ignore=shutil.ignore_patterns("Dockerfile.spacedoctor", "*.bin", "*.pt",
                                                                                     "*.pth", "*.ckpt", "*.safetensors", "*.onnx"))
            shutil.rmtree(space_dir / "outputs", ignore_errors=True)
            if outs.exists():
                shutil.copytree(outs, space_dir / "outputs")
            saved_rank = rank
        if functional:
            break
    tiers = ["functional", "api"]
    best = next((t for t in tiers if any(a["stage"] == t for a in attempts)), None)
    revived = best is not None
    case = {"space": sid, "likes": rec["likes"], "hf_exception": rec["hf_exception"], "revived": revived, "tier": best,
            "gpu": sandbox.GPU,
            "attempts": attempts, "calls": calls, "wall_secs": round(time.time() - t_start),
            "tokens": {k: sum((c["usage"] or {}).get(k, 0) for c in calls) for k in ("prompt_tokens", "completion_tokens")}}
    json.dump(case, open(space_dir / "case.json", "w"), indent=1)
    print(f"{sid:55s} revived={revived} tier={best} attempts={len(attempts)} "
          f"stages={[a['stage'] for a in attempts]} tokens={case['tokens']}", flush=True)
    return case


if __name__ == "__main__":
    import concurrent.futures as cf
    root = Path("/data/repro")
    dirs = [root / s.replace("/", "__") for s in sys.argv[1:]] if len(sys.argv) > 1 else \
        [d for d in sorted(root.iterdir(), key=lambda d: -int(json.load(open(d / "repro.json"))["likes"]) if (d / "repro.json").exists() else 0)
         if (d / "repro.json").exists() and not (d / "case.json").exists()
         and json.load(open(d / "repro.json"))["our_stage"] in ("runtime_error", "build_error")  # still broken today
         and not NSFW.search(d.name)]
    def safe(d):
        if STOP.is_set():
            return
        try:
            return treat(d)
        except beam.BudgetExhausted as e:  # keep the rest for after the 00:00 UTC reset
            STOP.set()
            print(f"{d.name}: BUDGET STOP {e}", flush=True)
        except Exception as e:  # one Space failing (API outage, disk) must not stop the batch
            print(f"{d.name}: harness error {e!r}", flush=True)

    with cf.ThreadPoolExecutor(int(os.environ.get("SD_WORKERS", "6"))) as ex:
        list(ex.map(safe, dirs))
