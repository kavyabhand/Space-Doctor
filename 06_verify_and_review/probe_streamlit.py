"""Render check for Streamlit apps, which expose no API to call: load the page in headless Chromium, wait for the
app to render, and require visible content and no Streamlit exception box. Saves a screenshot as the output.
usage: probe_streamlit.py URL [OUT_DIR]; prints one JSON line like probe.py."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url, outdir = sys.argv[1], (Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None)
res = {"endpoint": "page render", "ok": False, "inputs": [], "via": "browser"}
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(url, wait_until="domcontentloaded", timeout=120_000)
        pg.wait_for_selector('[data-testid="stApp"], .stApp', timeout=120_000)
        pg.wait_for_timeout(25_000)  # let the script run to completion (models load, widgets render)
        exc = pg.locator('[data-testid="stException"], .stException').count()
        running = pg.locator('[data-testid="stStatusWidget"]').count()
        text = pg.locator('[data-testid="stApp"], .stApp').first.inner_text(timeout=10_000)
        files = []
        if outdir:
            outdir.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(outdir / "page_render.png"))
            files = ["page_render.png"]
        ok = exc == 0 and len(text.strip()) > 40
        res.update(ok=ok, output_summary=text.strip()[:400], files=files,
                   **({} if ok else {"error": f"{exc} Streamlit exception box(es)" if exc else "page rendered almost no content"}))
        if running:
            res["note"] = "script still running at check time"
        b.close()
except Exception as e:
    res["error"] = repr(e)[:400]
print(json.dumps(res), flush=True)
