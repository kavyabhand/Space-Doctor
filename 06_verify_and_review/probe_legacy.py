"""Functional probe for gradio 3.x apps that predate gradio_client: speaks the old protocol directly.
usage: probe_legacy.py URL [REPO_DIR] [OUT_DIR]
Reads /config, picks the main event (an api_name, or the first click/submit wired to a rich input), builds inputs per
component (the Space's own example files when it ships them), and calls it through the websocket queue when the app
queues, else POST /api/predict. Same output contract as probe.py: one JSON line per endpoint tried."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import base64, json, math, re, struct, sys, tempfile, uuid, wave, zlib
from pathlib import Path

import requests
from websockets.sync.client import connect

url = sys.argv[1].rstrip("/") + "/"
repo = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
outdir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
TEXT = __import__("os").environ.get("SD_PROBE_TEXT", "a photo of a red apple on a wooden table")
RICH = {"image", "audio", "video", "textbox", "file", "chatbot", "sketchpad", "gallery"}


def repo_file(exts):
    if not repo or not repo.exists():
        return None
    fs = [p for p in repo.rglob("*") if p.is_file() and p.suffix.lower() in exts and ".git" not in p.parts and 2_000 < p.stat().st_size < 5_000_000]
    fs.sort(key=lambda p: (not re.search(r"example|sample|demo|test|input", str(p), re.I), len(p.parts), str(p)))
    return fs[0] if fs else None


def synth_png():
    w = h = 256
    raw = b"".join(b"\x00" + b"".join(bytes((x % 256, y % 256, 128)) for x in range(w)) for y in range(h))
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b"")


def synth_wav():
    p = Path(tempfile.mkdtemp()) / "probe.wav"
    with wave.open(str(p), "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
        f.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(32000)))
    return p.read_bytes()


img = repo_file({".jpg", ".jpeg", ".png", ".webp"})
aud = repo_file({".wav", ".mp3", ".flac", ".ogg"})
IMG = (img.read_bytes(), "image/" + ("jpeg" if img and img.suffix.lower() in (".jpg", ".jpeg") else (img.suffix[1:] if img else "png"))) if img else (synth_png(), "image/png")
AUD = (aud.read_bytes(), "audio/" + (aud.suffix[1:].replace("mp3", "mpeg") if aud else "wav")) if aud else (synth_wav(), "audio/wav")
durl = lambda b, mime: f"data:{mime};base64," + base64.b64encode(b).decode()
shown_img = str(img) if img else "generated test image"
shown_aud = str(aud) if aud else "generated test audio"


def value(comp):
    t, pr = comp.get("type", ""), comp.get("props", {})
    if t in ("image", "sketchpad"):
        return durl(*IMG), shown_img
    if t == "audio":
        return {"name": "probe.wav", "data": durl(*AUD)}, shown_aud
    if t == "file":
        return {"name": "probe.png", "data": durl(*IMG)}, shown_img
    if t in ("textbox", "text"):
        return (pr.get("value") or TEXT), (pr.get("value") or TEXT)
    if t in ("dropdown", "radio"):
        v = pr.get("value") or (pr.get("choices") or [None])[0]
        return v, str(v)
    if t in ("slider", "number", "checkbox", "checkboxgroup", "state", "colorpicker"):
        return pr.get("value"), str(pr.get("value"))
    if t == "chatbot":
        return [], "[]"
    return pr.get("value"), str(pr.get("value"))


def save_out(out, name):
    files = []
    for i, x in enumerate(out if isinstance(out, list) else [out]):
        s = x.get("data") if isinstance(x, dict) else x
        if isinstance(s, str) and s.startswith("data:") and ";base64," in s and outdir:
            outdir.mkdir(parents=True, exist_ok=True)
            mime, b64 = s[5:].split(";base64,", 1)
            ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "audio/wav": ".wav", "audio/x-wav": ".wav",
                   "audio/mpeg": ".mp3", "video/mp4": ".mp4"}.get(mime, ".bin")
            data = base64.b64decode(b64)
            if data:
                p = outdir / f"{name}_{i}{ext}"; p.write_bytes(data); files.append(p.name)
    return files


def nonempty(x):
    if x is None:
        return False
    if isinstance(x, str):
        return bool(x.strip())
    if isinstance(x, (list, tuple)):
        return any(nonempty(v) for v in x)
    if isinstance(x, dict):
        return any(nonempty(v) for v in x.values())
    return True


cfg = requests.get(url + "config", timeout=30).json()
comps = {c["id"]: c for c in cfg.get("components", [])}
deps = list(enumerate(cfg.get("dependencies", [])))
HELPER = re.compile(r"clear|reset|example|load|change|select|toggle|refresh|upload", re.I)
def score(item):
    i, d = item
    ins = [comps.get(x, {}).get("type", "") for x in d.get("inputs", [])]
    name = d.get("api_name") or ""
    return (bool(HELPER.search(name)), not d.get("api_name"), d.get("trigger") not in ("click", "submit"), -len(set(ins) & RICH), i)
cands = [x for x in sorted(deps, key=score) if x[1].get("inputs") and x[1].get("outputs") and x[1].get("backend_fn", True)][:3]
if not cands:
    print(json.dumps({"endpoint": None, "ok": False, "error": "no callable events in config"}))
for fn, d in cands:
    name = d.get("api_name") or f"fn_index:{fn}"
    # An event whose outputs are only numbers, toggles or state (a seed randomizer, a slider sync) proves nothing.
    out_types = {comps.get(x, {}).get("type", "") for x in d.get("outputs", [])}
    trivial = not (out_types & (RICH | {"label", "json", "html", "markdown", "highlightedtext", "dataframe", "plot", "model3d"}))
    pairs = [value(comps.get(x, {})) for x in d["inputs"]]
    data, shown = [p[0] for p in pairs], [p[1][:80] for p in pairs]
    try:
        if cfg.get("enable_queue") and d.get("queue") is not False:
            ws_url = re.sub(r"^http", "ws", url) + "queue/join"
            h = uuid.uuid4().hex[:10]
            with connect(ws_url, open_timeout=30, max_size=2 ** 26) as ws:
                out, ok = None, False
                while True:
                    m = json.loads(ws.recv(timeout=540))
                    if m.get("msg") == "send_hash":
                        ws.send(json.dumps({"fn_index": fn, "session_hash": h}))
                    elif m.get("msg") == "send_data":
                        ws.send(json.dumps({"data": data, "fn_index": fn, "session_hash": h, "event_data": None}))
                    elif m.get("msg") == "process_completed":
                        ok, out = m.get("success", True), (m.get("output") or {}).get("data")
                        err = (m.get("output") or {}).get("error")
                        break
                    elif m.get("msg") == "queue_full":
                        raise RuntimeError("queue full")
        else:
            r = requests.post(url + "api/predict/", json={"data": data, "fn_index": fn}, timeout=540)
            j = r.json()
            ok, out, err = r.ok and "data" in j, j.get("data"), j.get("error")
        ok = ok and nonempty(out)
        files = save_out(out, name.strip("/").replace("/", "_").replace(":", "") or "out") if ok else []
        summary = repr([x if not (isinstance(x, str) and x.startswith("data:")) else x[:40] + "…(base64)" for x in (out or [])])[:400]
        print(json.dumps({"endpoint": name, "ok": bool(ok), "helper": bool(HELPER.search(d.get("api_name") or "")) or trivial, "inputs": shown,
                          "output_summary": summary, "files": files, "via": "legacy", **({} if ok else {"error": str(err or "empty output")[:400]})}), flush=True)
        if ok and not trivial:
            break
    except Exception as e:
        print(json.dumps({"endpoint": name, "ok": False, "inputs": shown, "error": repr(e)[:400], "via": "legacy"}), flush=True)
