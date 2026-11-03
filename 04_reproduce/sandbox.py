"""Rebuild a Hugging Face Gradio/Streamlit Space in Docker the way the Spaces builder does,
then boot it and smoke-test it. Used both to reproduce the original failure and to verify fixes.

The emulation follows the documented Spaces build for SDK spaces:
  python:{python_version} base, apt packages.txt, pip install -r requirements.txt,
  then the SDK pinned to sdk_version from the README front-matter, then `python app_file`.
Resources match cpu-basic (2 vCPU, 16 GB).
"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, os, re, shutil, subprocess, sys, time, uuid
from pathlib import Path

import yaml
import requests

SPACES_ROOT = Path(os.environ.get("SD_WORK", "/data/work"))
TEXT_EXT = {".py", ".txt", ".md", ".toml", ".cfg", ".yaml", ".yml", ".json", ".sh", ".ini", ".js", ".css", ".html"}


def front_matter(readme: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", readme, re.S)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


def fetch_space(space_id: str, dest: Path, max_file_mb=300) -> Path:
    """Download the Space repo into dest. Everything the app may load at startup (examples, small weights)
    is kept; only individual files over max_file_mb are skipped."""
    from huggingface_hub import HfApi, snapshot_download
    files = [f.path for f in HfApi().list_repo_tree(space_id, repo_type="space", recursive=True)
             if getattr(f, "size", None) is not None and f.size <= max_file_mb * 1024 * 1024]
    if dest.exists():
        shutil.rmtree(dest)
    snapshot_download(repo_id=space_id, repo_type="space", local_dir=str(dest), allow_patterns=files)
    return dest


def python_for(meta: dict, hf_error: str = "") -> str:
    """README pin wins; otherwise use the interpreter the real Spaces builder used (visible in its log)."""
    if meta.get("python_version"):
        return str(meta["python_version"])
    m = re.findall(r"/python(3\.\d+)/", hf_error or "")
    return m[-1] if m else "3.10"


GPU = os.environ.get("SD_GPU") == "1"
_BOOT_LOCK = __import__("threading").Lock()   # GPU box: real CUDA wheels from PyPI and --gpus all, like GPU Spaces


def dockerfile_for(meta: dict, repo: Path, timetravel: str = "") -> str:
    """timetravel='2024-03-01T00:00:00Z' builds the no-LLM baseline: every package resolved as of that date (uv
    --exclude-newer), on the Python the Space was written for. Otherwise the Spaces recipe as it runs today."""
    sdk = meta.get("sdk", "gradio")
    py = ".".join(str(meta.get("_python") or python_for(meta)).split(".")[:2])  # base images are tagged by minor version
    sdk_version = meta.get("sdk_version")
    # Deviation from Spaces, documented: on the CPU box, CPU torch wheels (same Python API, no multi-GB CUDA libs)
    # and a shared BuildKit pip cache, so dozens of rebuilds fit on one machine. cpu-basic Spaces never touch CUDA.
    idx = "" if GPU else " PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu"
    lines = ["# syntax=docker/dockerfile:1", f"FROM python:{py}",
             f"ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1{idx}",
             "RUN apt-get update && apt-get install -y git git-lfs ffmpeg libsm6 libxext6 cmake rsync libgl1 && rm -rf /var/lib/apt/lists/*"]
    if (repo / "packages.txt").exists():
        lines += ["COPY packages.txt /tmp/packages.txt",
                  "RUN apt-get update && xargs -r -a /tmp/packages.txt apt-get install -y && rm -rf /var/lib/apt/lists/*"]
    lines += ["RUN pip install --upgrade pip"]
    if timetravel:
        # PyPI only: the PyTorch index publishes no upload dates, so --exclude-newer cannot apply to it.
        inst = f'RUN --mount=type=cache,target=/root/.cache/uv pip install uv && uv pip install --system --exclude-newer {timetravel}'
        lines += ["ENV PIP_EXTRA_INDEX_URL="]
        if (repo / "requirements.txt").exists():
            lines += ["COPY requirements.txt /tmp/requirements.txt", f"{inst} -r /tmp/requirements.txt"]
        if sdk == "gradio" and sdk_version:
            lines += [f'{inst} "gradio[oauth]=={sdk_version}" "uvicorn>=0.14.0" spaces']
        elif sdk == "streamlit" and sdk_version:
            lines += [f'{inst} "streamlit=={sdk_version}"']
    else:
        if (repo / "requirements.txt").exists():
            lines += ["COPY requirements.txt /tmp/requirements.txt",
                      "RUN --mount=type=cache,target=/root/.cache/pip pip install -r /tmp/requirements.txt"]
        if sdk == "gradio" and sdk_version:
            lines += [f'RUN --mount=type=cache,target=/root/.cache/pip pip install "gradio[oauth]=={sdk_version}" "uvicorn>=0.14.0" spaces']
        elif sdk == "streamlit" and sdk_version:
            lines += [f'RUN --mount=type=cache,target=/root/.cache/pip pip install "streamlit=={sdk_version}"']
    lines += ["WORKDIR /home/user/app", "COPY . /home/user/app",
              "ENV GRADIO_SERVER_NAME=0.0.0.0 GRADIO_SERVER_PORT=7860 SYSTEM=spaces PYTHONUNBUFFERED=1"]
    app = meta.get("app_file", "app.py")
    if sdk == "streamlit":
        lines += [f'CMD ["streamlit", "run", "{app}", "--server.port", "7860", "--server.address", "0.0.0.0"]']
    else:
        lines += [f'CMD ["python", "{app}"]']
    return "\n".join(lines) + "\n"


def sh(cmd, timeout=None, **kw):
    p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True,
                       timeout=timeout, errors="replace", **kw)
    return p.returncode, p.stdout + p.stderr


def tail(s: str, n=6000) -> str:
    return s if len(s) <= n else "...[truncated]...\n" + s[-n:]


def build_and_test(repo: Path, meta: dict, tag: str, boot_timeout=900, build_timeout=2400, keep_image=False,
                   outdir: Path = None, timetravel: str = "") -> dict:
    """Return dict(stage=build_error|runtime_error|timeout|running, logs=..., api=..., probe=..., functional=...)."""
    (repo / "Dockerfile.spacedoctor").write_text(dockerfile_for(meta, repo, timetravel))
    t0 = time.time()
    try:
        rc, out = sh(["docker", "buildx", "build", "--load", "--progress=plain", "-f", "Dockerfile.spacedoctor", "-t", tag, "."], cwd=repo, timeout=build_timeout)
    except subprocess.TimeoutExpired:
        return {"stage": "build_timeout", "logs": "docker build exceeded timeout", "secs": time.time() - t0}
    if rc != 0:
        return {"stage": "build_error", "logs": tail(out), "secs": time.time() - t0}
    # Images are ~5 GB each; keep only what we need (the resolved package set), then delete the image.
    try:
        _, freeze = sh(["docker", "run", "--rm", "--entrypoint", "pip", tag, "freeze"], timeout=300)
    except subprocess.TimeoutExpired:
        freeze = ""
    try:
        if GPU:  # one GPU: serialize boots so two apps never compete for VRAM
            with _BOOT_LOCK:
                res = _boot_and_probe(tag, meta, boot_timeout, t0, repo, outdir)
        else:
            res = _boot_and_probe(tag, meta, boot_timeout, t0, repo, outdir)
    finally:
        if not keep_image:
            sh(["docker", "rmi", "-f", tag])
    res["freeze"] = freeze
    return res


def _boot_and_probe(tag, meta, boot_timeout, t0, repo=None, outdir=None):
    name = f"sd-{uuid.uuid4().hex[:8]}"
    res_args = ["--gpus", "all", "--memory", "15g"] if GPU else ["--cpus", "2", "--memory", "16g"]
    rc, out = sh(["docker", "run", "-d", "--name", name, *res_args, "-p", "127.0.0.1::7860", tag])
    if rc != 0:
        return {"stage": "runtime_error", "logs": tail(out), "secs": time.time() - t0}
    try:
        _, port_out = sh(["docker", "port", name, "7860"])
        port = port_out.strip().splitlines()[0].rsplit(":", 1)[-1]
        url = f"http://127.0.0.1:{port}/"
        deadline = time.time() + boot_timeout
        while time.time() < deadline:
            _, st = sh(["docker", "inspect", "-f", "{{.State.Running}} {{.State.ExitCode}}", name])
            if st.startswith("false"):
                _, logs = sh(["docker", "logs", name])
                return {"stage": "runtime_error", "logs": tail(logs), "secs": time.time() - t0}
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(5)
        else:
            _, logs = sh(["docker", "logs", name])
            return {"stage": "boot_timeout", "logs": tail(logs), "secs": time.time() - t0}
        # App answers HTTP. Ask it for its API schema like a client would.
        api = None
        if meta.get("sdk", "gradio") == "gradio":
            rc, api_out = sh([sys.executable, "-c",
                              "import sys,json;from gradio_client import Client;"
                              "c=Client(sys.argv[1],verbose=False);"
                              "info=c.view_api(return_format='dict',print_info=False);"
                              "print(json.dumps({'named':list(info.get('named_endpoints',{})),"
                              "'unnamed':len(info.get('unnamed_endpoints',{}))}))", url], timeout=120)
            api = api_out.strip().splitlines()[-1] if rc == 0 and api_out.strip() else f"API_ERROR: {tail(api_out, 1500)}"
        probe = []
        if meta.get("sdk") == "streamlit":  # no API to call: render the page in a browser instead
            try:
                _, pout = sh([sys.executable, str(_ROOT.joinpath("06_verify_and_review", "probe_streamlit.py")), url, str(outdir) if outdir else ""], timeout=300)
                probe = [json.loads(l) for l in pout.splitlines() if l.startswith("{")] or [{"ok": False, "error": tail(pout, 600)}]
            except subprocess.TimeoutExpired:
                probe = [{"ok": False, "error": "render check timed out"}]
        if meta.get("sdk", "gradio") == "gradio":
            probe = _probe_inside(name, outdir)  # the app's own gradio_client matches its server's protocol
            api_ok_inside = any(p.get("endpoint") for p in probe)
            if api_ok_inside and str(api).startswith("API_ERROR"):
                api = json.dumps({"named": [p["endpoint"] for p in probe], "via": "in-container client"})
        if not probe and api and not str(api).startswith("API_ERROR"):
            try:
                _, pout = sh([sys.executable, str(_ROOT.joinpath("06_verify_and_review", "probe.py")), url, str(repo or ""),
                              str(outdir) if outdir else ""], timeout=600)
                probe = [json.loads(l) for l in pout.splitlines() if l.startswith("{")] or [{"ok": False, "error": tail(pout, 800)}]
            except subprocess.TimeoutExpired:
                probe = [{"ok": False, "error": "probe timed out after 600s"}]
        if meta.get("sdk", "gradio") == "gradio" and not any(p.get("ok") and not p.get("helper") for p in probe) and \
                (not probe or any("Unknown protocol" in str(p.get("error", "")) or "no endpoints" in str(p.get("error", ""))
                                  for p in probe)):
            try:  # gradio 3.x apps older than gradio_client: speak the legacy queue protocol directly
                _, pout = sh([sys.executable, str(_ROOT.joinpath("06_verify_and_review", "probe_legacy.py")), url, str(repo or ""),
                              str(outdir) if outdir else ""], timeout=600)
                legacy = [json.loads(l) for l in pout.splitlines() if l.startswith("{")]
                if legacy:
                    probe = probe + legacy
                    if str(api).startswith("API_ERROR") and any(p.get("endpoint") for p in legacy):
                        api = json.dumps({"named": [p["endpoint"] for p in legacy], "via": "legacy"})
            except subprocess.TimeoutExpired:
                probe = probe + [{"ok": False, "error": "legacy probe timed out", "via": "legacy"}]
        _, logs = sh(["docker", "logs", name])
        return {"stage": "running", "logs": tail(logs, 3000), "api": api, "probe": probe,
                # Only a real (non-helper) endpoint returning a non-empty result counts.
                "functional": any(p.get("ok") and not p.get("helper") for p in probe), "secs": time.time() - t0}
    finally:
        sh(["docker", "rm", "-f", name])


CONFIG = ("README.md", "requirements.txt", "packages.txt", "pre-requirements.txt", "setup.py", "pyproject.toml",
          "setup.cfg", "Dockerfile", "environment.yml")


def _probe_inside(name, outdir):
    """Run probe.py inside the app's container against 127.0.0.1:7860 with the gradio_client that ships with the
    app's gradio, then copy the outputs out. Returns [] if the container has no usable client."""
    sh(["docker", "cp", str(_ROOT.joinpath("06_verify_and_review", "probe.py")), f"{name}:/tmp/sd_probe.py"])
    try:
        envs = [x for k in ("SD_PROBE_TEXT", "SD_PROBE_CHOICE") if os.environ.get(k) for x in ("-e", f"{k}={os.environ[k]}")]
        rc, pout = sh(["docker", "exec", *envs, name, "python", "/tmp/sd_probe.py", "http://127.0.0.1:7860/", "/home/user/app",
                       "/tmp/sd_out"], timeout=600)
    except subprocess.TimeoutExpired:
        return [{"ok": False, "error": "probe timed out after 600s", "via": "container"}]
    lines = [json.loads(l) for l in pout.splitlines() if l.startswith("{")]
    if not lines:
        return [] if re.search(r"ModuleNotFoundError|ImportError|SyntaxError", pout) else \
            [{"ok": False, "error": tail(pout, 800), "via": "container"}]
    if outdir:
        Path(outdir).mkdir(parents=True, exist_ok=True)
        sh(["docker", "cp", f"{name}:/tmp/sd_out/.", str(outdir)])
    for l in lines:
        l["via"] = "container"
    return lines


def repo_text(repo: Path, max_file=40_000, max_total=240_000, first=()) -> str:
    """The Space's text files for the model's context, most relevant first: config files, the app file and any
    file named in the logs (`first`), then other Python files (shallow and small first), then other text.
    Files that do not fit are listed by name as omitted, so the model knows they exist and can ask for them."""
    files = []
    for p in repo.rglob("*"):
        if not p.is_file() or ".git" in p.parts or p.name == "Dockerfile.spacedoctor" or ".cache" in p.parts:
            continue
        if p.suffix.lower() not in TEXT_EXT and p.name not in ("requirements.txt", "packages.txt", "Dockerfile"):
            continue
        rel = p.relative_to(repo).as_posix()
        size = p.stat().st_size
        if rel in CONFIG or rel in first:
            rank = (0, CONFIG.index(rel) if rel in CONFIG else 50, 0)
        elif p.suffix == ".py":
            rank = (1, len(p.relative_to(repo).parts), size)
        else:
            rank = (2, len(p.relative_to(repo).parts), size)
        files.append((rank, rel, p))
    parts, omitted, total = [], [], 0
    for _, rel, p in sorted(files):
        try:
            t = p.read_text(errors="replace")
        except Exception:
            continue
        if len(t) > max_file:
            t = t[:max_file] + "\n...[file truncated]..."
        chunk = f"\n===== FILE: {rel} =====\n{t}"
        if total + len(chunk) > max_total:
            omitted.append(rel)
            continue
        parts.append(chunk)
        total += len(chunk)
    if omitted:
        parts.append("\n===== NOT SHOWN (context budget; ask for any you need with \"need_files\") =====\n" + "\n".join(omitted[:400]))
    return "".join(parts)


def read_files(repo: Path, paths, max_file=40_000) -> str:
    out = []
    for rel in paths[:12]:
        p = (repo / rel).resolve()
        if repo.resolve() not in p.parents or not p.is_file():
            out.append(f"\n===== FILE: {rel} ===== (does not exist)")
            continue
        t = p.read_text(errors="replace")
        out.append(f"\n===== FILE: {rel} =====\n{t[:max_file]}" + ("\n...[file truncated]..." if len(t) > max_file else ""))
    return "".join(out)


if __name__ == "__main__":
    sid = sys.argv[1]
    d = SPACES_ROOT / sid.replace("/", "__") / "orig"
    fetch_space(sid, d)
    meta = front_matter((d / "README.md").read_text(errors="replace")) if (d / "README.md").exists() else {}
    meta["_python"] = python_for(meta, sys.argv[2] if len(sys.argv) > 2 else "")
    res = build_and_test(d, meta, tag="sd-" + re.sub(r"[^a-z0-9]", "-", sid.lower())[:60])
    print(json.dumps({"space": sid, "meta": meta, **res}, indent=1)[:8000])
