"""Minimal Beam client with a hard daily-budget guard.

Reflection's free tier (read from the API's own x-ratelimit-* headers) allows 1M output tokens and 10M uncached
input tokens per day, resetting at 00:00 UTC. Every call is logged to a ledger, and a call is refused before it is
sent if the remaining daily budget would drop below a reserve. Running out mid-run would strand half-treated Spaces.
"""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, os, threading, time
from pathlib import Path

import requests

_env = Path(__file__).resolve().parent.parent / ".env"
for p in (_env, Path("/data/.env")):
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

# Several keys (REFLECTION_API_KEY, REFLECTION_API_KEY_2, ...) are used in order: when one reaches its daily budget,
# calls move to the next. Each key's remaining budget is tracked separately from the API's own headers.
KEYS = [os.environ[k] for k in ("REFLECTION_API_KEY", "REFLECTION_API_KEY_2", "REFLECTION_API_KEY_3") if os.environ.get(k)]
if KEYS:
    BASE, KEY, MODEL = "https://api.reflection.ai/openai/v1", KEYS[0], "Beam-1.0-501B-A23B"
else:
    BASE, KEY, MODEL = "https://router.huggingface.co/v1", os.environ.get("HF_TOKEN", ""), "reflection/Beam-1.0-501B-A23B:auto"
    KEYS = [KEY]

LEDGER = Path(os.environ.get("BEAM_LEDGER", "/data/beam_ledger.jsonl"))
RESERVE_OUT = int(os.environ.get("BEAM_RESERVE_OUT", "50000"))      # output tokens kept back each day
RESERVE_IN = int(os.environ.get("BEAM_RESERVE_IN", "1000000"))       # uncached input tokens kept back each day
_lock = threading.Lock()
_rem = [{"out": None, "in": None} for _ in KEYS]
_remaining = _rem[0]  # the active key's budget (kept for remaining())
_active = [0]
_inflight = [0 for _ in KEYS]  # output tokens reserved by calls still running, per key


class BudgetExhausted(RuntimeError):
    pass


def _note(headers, i):
    try:
        _rem[i]["out"] = int(headers["x-ratelimit-remaining-output-tokens-day"])
        _rem[i]["in"] = int(headers["x-ratelimit-remaining-uncached-input-tokens-day"])
    except (KeyError, ValueError):
        pass


def remaining():
    return [dict(r) for r in _rem]


def _learn(i):
    """Read key i's remaining daily budget with one tiny request before any real call is allowed on it."""
    try:
        r = requests.post(f"{BASE}/chat/completions", timeout=60, headers={"Authorization": f"Bearer {KEYS[i]}"},
                          json={"model": MODEL, "messages": [{"role": "user", "content": "Reply OK."}],
                                "reasoning_effort": "low", "max_completion_tokens": 32})
        _note(r.headers, i)
    except requests.RequestException:
        pass
    if _rem[i]["out"] is None:  # still unknown: treat the key as unusable rather than guess
        _rem[i]["out"] = 0


def _fits(i, max_tokens, est_in):
    # Every running call may still use up to its max_tokens, so count those as spent: usage can never pass the
    # free daily allowance even with many calls in parallel.
    r = _rem[i]
    return not ((r["out"] is not None and r["out"] - _inflight[i] - max_tokens < RESERVE_OUT) or
                (r["in"] is not None and r["in"] - est_in < RESERVE_IN))


def chat(messages, effort="medium", max_tokens=16000, retries=3, token=None, tag=""):
    """Returns dict(content, reasoning, usage, finish_reason, secs, effort). Raises BudgetExhausted or RuntimeError."""
    est_in = sum(len(m.get("content") or "") for m in messages) // 3  # conservative chars->tokens
    with _lock:
        if not token and BASE.startswith("https://api.reflection.ai"):
            for i in range(_active[0], len(KEYS)):
                if _rem[i]["out"] is None:
                    _learn(i)
        ki = next((i for i in range(_active[0], len(KEYS)) if _fits(i, max_tokens, est_in)), None)
        if ki is None and not token:
            raise BudgetExhausted(f"all {len(KEYS)} key(s) at their daily budget: {remaining()}")
        _active[0] = ki or 0
        _inflight[ki or 0] += max_tokens
    try:
        return _call(messages, effort, max_tokens, retries, token, tag, ki, est_in)
    finally:
        with _lock:
            _inflight[ki or 0] -= max_tokens


def _call(messages, effort, max_tokens, retries, token, tag, ki, est_in):
    base, key, model = (("https://router.huggingface.co/v1", token, "reflection/Beam-1.0-501B-A23B:auto")
                        if token else (BASE, KEYS[ki], MODEL))
    body = {"model": model, "messages": messages, "reasoning_effort": effort, "max_completion_tokens": max_tokens}
    last = None
    for i in range(retries):
        t0 = time.time()
        try:
            r = requests.post(f"{base}/chat/completions", json=body, timeout=1800,
                              headers={"Authorization": f"Bearer {key}"})
            _note(r.headers, ki or 0)
            if r.status_code == 429:
                txt = r.text[:300]
                if "day" in txt.lower() or (_rem[ki or 0]["out"] is not None and _rem[ki or 0]["out"] < max_tokens):
                    with _lock:
                        _rem[ki or 0]["out"] = 0  # mark this key spent; the next call moves to the next key
                    if ki is not None and ki + 1 < len(KEYS):
                        return chat(messages, effort, max_tokens, retries, token, tag)
                    raise BudgetExhausted(f"429 daily limit: {txt}")
                last = f"429 {txt}"
                time.sleep(20 * (i + 1))
                continue
            if r.status_code in (500, 502, 503, 504):
                last = f"{r.status_code} {r.text[:300]}"
                time.sleep(15 * (i + 1))
                continue
            r.raise_for_status()
            j = r.json()
            ch = j["choices"][0]
            msg = ch["message"]
            out = {"content": msg.get("content") or "",
                   "reasoning": msg.get("reasoning_content") or msg.get("reasoning") or "",
                   "usage": j.get("usage", {}), "finish_reason": ch.get("finish_reason"),
                   "secs": round(time.time() - t0, 1), "effort": effort}
            with _lock:
                LEDGER.parent.mkdir(parents=True, exist_ok=True)
                with open(LEDGER, "a") as f:
                    f.write(json.dumps({"t": time.time(), "tag": tag, "effort": effort, "usage": out["usage"],
                                        "finish": out["finish_reason"], "secs": out["secs"], "key": (ki or 0) + 1,
                                        "remaining": dict(_rem[ki or 0])}) + "\n")
            return out
        except requests.RequestException as e:
            last = repr(e)
            time.sleep(15 * (i + 1))
    raise RuntimeError(f"Beam call failed: {last}")
