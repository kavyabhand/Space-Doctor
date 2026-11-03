"""Functional probe: call a running Gradio app's main endpoint(s) with inputs built from its API schema.

usage: probe.py URL [REPO_DIR] [OUT_DIR]
Inputs prefer the Space's own example files (an image/audio file shipped in the repo), else a synthetic one.
Helper endpoints (clear buttons, example loaders, lambdas) are tried last. A call only counts as ok if it returns
a non-empty result; returned files must exist and be non-empty. Output files are copied to OUT_DIR for review.
Prints one JSON line per endpoint tried."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, math, re, shutil, struct, sys, tempfile, wave, zlib
from pathlib import Path

from gradio_client import Client
try:
    from gradio_client import handle_file
except ImportError:  # gradio_client < 1.0 (gradio 3.x / early 4.x) takes plain file paths
    def handle_file(path):
        return path

url = sys.argv[1]
repo = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
outdir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
tmp = Path(tempfile.mkdtemp())
IMG_EXT, AUD_EXT, VID_EXT = {".jpg", ".jpeg", ".png", ".webp"}, {".wav", ".mp3", ".flac", ".ogg"}, {".mp4"}


def png(path, w=256, h=256):
    raw = b"".join(b"\x00" + b"".join(bytes((x % 256, y % 256, 128)) for x in range(w)) for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                     chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path


def wav(path, secs=2.0, sr=16000):
    with wave.open(str(path), "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
        f.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / sr))) for i in range(int(secs * sr))))
    return path


def repo_file(exts):
    if not repo or not repo.exists():
        return None
    files = [p for p in repo.rglob("*") if p.is_file() and p.suffix.lower() in exts and ".git" not in p.parts
             and 2_000 < p.stat().st_size < 5_000_000]
    files.sort(key=lambda p: (not re.search(r"example|sample|demo|test|input", str(p), re.I), len(p.parts), str(p)))
    return files[0] if files else None


IMG = repo_file(IMG_EXT) or png(tmp / "probe.png")
AUD = repo_file(AUD_EXT) or wav(tmp / "probe.wav")
VID = repo_file(VID_EXT)
TEXT = __import__("os").environ.get("SD_PROBE_TEXT", "a photo of a red apple on a wooden table")


def _swap_files(x, path):
    """Replace every file reference inside gradio's own example input with our file, keeping its structure."""
    if isinstance(x, dict):
        if x.get("meta", {}).get("_type") == "gradio.FileData" or ("path" in x and ("url" in x or "orig_name" in x)):
            return handle_file(str(path))
        return {k: _swap_files(v, path) for k, v in x.items()}
    if isinstance(x, list):
        return [_swap_files(v, path) for v in x]
    return x


def value_for(p):
    comp = (p.get("component") or "").lower()
    ex = p.get("example_input")
    want = __import__("os").environ.get("SD_PROBE_CHOICE")
    if want and comp in ("dropdown", "radio"):  # pick a specific option (e.g. the language that matches the example clip)
        ch = (p.get("type") or {}).get("enum") if isinstance(p.get("type"), dict) else None
        hit = next((c for c in (ch or []) if want.lower() in str(c).lower()), None)
        if hit is not None:
            return hit
    if ex is not None and not p.get("parameter_has_default"):
        # gradio publishes a schema-valid example per input; use it, with the Space's own media where it has some
        f = IMG if comp in ("image", "imageeditor", "sketchpad", "annotatedimage", "gallery", "imageslider", "file", "uploadbutton") \
            else AUD if comp in ("audio", "microphone") else (VID or IMG) if comp == "video" else None
        if f is not None:
            return _swap_files(ex, f)
        if isinstance(ex, str) and comp in ("textbox", "textarea", "text") and ex.strip().lower() in ("", "hello!!", "hello"):
            return TEXT
        return ex
    t = p.get("python_type", {}).get("type", "") if isinstance(p.get("python_type"), dict) else str(p.get("python_type"))
    if comp in ("image", "imageeditor", "sketchpad", "annotatedimage", "gallery", "imageslider"):
        v = handle_file(str(IMG))
        return {"background": v, "layers": [], "composite": v} if comp in ("imageeditor", "sketchpad") else ([v] if comp == "gallery" else v)
    if comp == "multimodaltextbox":
        return {"text": TEXT, "files": []}
    if comp == "dataframe":
        return p.get("parameter_default") if p.get("parameter_has_default") else {"headers": ["a"], "data": [["1"]]}
    if comp == "colorpicker":
        return "#ff0000"
    if comp in ("audio", "microphone"):
        return handle_file(str(AUD))
    if comp == "video":
        return {"video": handle_file(str(VID))} if VID else handle_file(str(IMG))
    if p.get("parameter_has_default"):
        return p.get("parameter_default")
    if comp in ("file", "uploadbutton", "model3d"):
        return handle_file(str(IMG))
    if comp in ("slider", "number"):
        return 1
    if comp == "checkbox":
        return False
    if comp in ("dropdown", "radio"):
        ch = (p.get("type") or {}).get("enum") if isinstance(p.get("type"), dict) else None
        return ch[0] if ch else None
    if comp == "chatbot":
        return []
    if "str" in t or comp in ("textbox", "text", "textarea", "code", "markdown"):
        return TEXT
    if "float" in t or "int" in t:
        return 1
    if "bool" in t:
        return False
    return None


HELPER = re.compile(r"lambda|clear|reset|example|update|change|load|select|toggle|show|hide|refresh|random|upload|login", re.I)
RICH = {"image", "audio", "video", "textbox", "gallery", "file", "chatbot", "model3d", "imageeditor", "sketchpad"}


def rank(item):
    name, spec = item
    comps = {(p.get("component") or "").lower() for p in spec.get("parameters", [])}
    return (bool(HELPER.search(name)), name != "/predict", -len(comps & RICH), name)


def files_in(x):
    if isinstance(x, str):
        return [x] if len(x) < 1000 and Path(x).is_file() else []
    if isinstance(x, dict):
        return [f for v in x.values() for f in files_in(v)]
    if isinstance(x, (list, tuple)):
        return [f for v in x for f in files_in(v)]
    return []


def empty(x):
    if x is None:
        return True
    if isinstance(x, str):
        return not x.strip()
    if isinstance(x, (list, tuple, dict)):
        return len(x) == 0 or all(empty(v) for v in (x.values() if isinstance(x, dict) else x))
    return False


try:
    c = Client(url, verbose=False)
except TypeError:  # very old clients have no verbose flag
    c = Client(url)
info = c.view_api(return_format="dict", print_info=False)
eps = sorted(info.get("named_endpoints", {}).items(), key=rank)[:3]
if not eps:  # old apps without api_name expose endpoints by index only
    eps = sorted(((f"fn_index:{k}", v) for k, v in (info.get("unnamed_endpoints") or {}).items()), key=rank)[:3]
if not eps:
    print(json.dumps({"endpoint": None, "ok": False, "error": "no endpoints"}))
for name, spec in eps:
    args = [value_for(p) for p in spec.get("parameters", [])]
    shown = [str(a.get("path") if isinstance(a, dict) and "path" in a else a)[:80] for a in args]
    try:
        out = c.predict(*args, fn_index=int(name.split(":")[1])) if name.startswith("fn_index:") else c.predict(*args, api_name=name)
        fs = files_in(out)
        bad = [f for f in fs if Path(f).stat().st_size == 0]
        ok = not empty(out) and not bad
        saved = []
        if ok and outdir and fs:
            outdir.mkdir(parents=True, exist_ok=True)
            for i, f in enumerate(fs[:4]):
                dst = outdir / f"{name.strip('/').replace('/', '_') or 'out'}_{i}{Path(f).suffix}"
                shutil.copy(f, dst)
                saved.append(dst.name)
        print(json.dumps({"endpoint": name, "ok": ok, "helper": bool(HELPER.search(name)), "inputs": shown,
                          "output_summary": repr(out)[:400], "files": saved,
                          **({"error": "empty or zero-byte output"} if not ok else {})}), flush=True)
        if ok and not HELPER.search(name):
            break
    except Exception as e:
        print(json.dumps({"endpoint": name, "ok": False, "inputs": shown, "error": repr(e)[:500]}), flush=True)
