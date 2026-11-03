# 05 · Repair with Beam

> One prompt holds everything a person would need to fix the Space. Then Beam decides how.

## What Beam sees

[`doctor.py`](doctor.py) builds one prompt per Space, in this order (fixed parts first, so retries hit
Reflection's prompt cache):

1. Hugging Face's own error log (tail)
2. our rebuild log of the untouched Space
3. the exact `pip freeze` the failing build resolved
4. **the Dockerfile the Space is built from**, noting that the SDK installs after `requirements.txt` and can
   re-upgrade a pin
5. short migration notes ([`migration_notes.md`](migration_notes.md)), marked as hints to verify against the logs
6. **the repository**: config files, the app file and any file named in a traceback first, then other Python
   files, then other text. Files that don't fit the budget are listed by name.

## What Beam can answer

One JSON object: a diagnosis that quotes the decisive log line, a category, a verdict (`fixable` / `unfixable`),
and edits as exact search/replace pairs or small full files. Two tools sit beside that:

- **`need_files`**: ask for files it was not shown, instead of guessing them.
- **`lock`**: ask for a lockfile resolved as of a date it picks (`uv pip compile --exclude-newer <date>
  --python-version <ver>`). Beam decides when an era-pinned stack is the honest fix and when a small code edit is.
  Of the 34 revivals, many combine both (for example, `SRDdev/Image-Caption`: a mid-2024 lockfile plus two
  modernized gradio calls).

## The tool loop: cheap checks before expensive ones

Within one attempt, before any Docker build:

- a patch whose search text isn't in the file, or a lockfile that doesn't resolve, goes straight back to Beam
  with the exact error (up to three turns);
- a `need_files` request is answered with the files.

Only a patch that applies cleanly is rebuilt. Multi-turn calls send back Beam's earlier `reasoning_content`.

## Escalation

`reasoning_effort` is medium, then medium, then high, and rises only after a failed rebuild, with the new logs in
the prompt. 18 revivals came at medium on the first attempt, 10 on the second, and 6 needed high on the third.

## Abstention

The system prompt allows `"verdict": "unfixable"` and says when it is right: owner-only secrets, gated or deleted
models, dead downloads, hardware the Space can't get. Beam used it 71 times. Examples: CodeGeeX needs its owner's
paid API key (Beam still named the Python 3.13 fix for the owner); Every-Text loads its whole app from a secret;
Real-Time-Voice-Cloning's weights sit behind a dead Google Drive link.

## Staying on the free tier

[`beam.py`](beam.py) is the Reflection API client:

- reads each key's remaining daily allowance from the API's own `x-ratelimit-*` headers, and learns it with one
  tiny request before any real work on that key;
- counts tokens promised to calls still running, so 20 parallel workers can never overshoot;
- stops before a key's free daily allowance runs out and moves to the next key;
- logs every call (tokens, effort, latency) to a ledger.

## Usage, in total

| | |
|---|---|
| Repair calls | 638 |
| Input tokens | 17.8M (7.3M served from Reflection's prompt cache) |
| Output tokens | 1.69M, reasoning included |
| Median Beam call | 10 s |
| Median time per Space, end to end | 13 min, almost all Docker builds |

| File | What it is |
|---|---|
| [`doctor.py`](doctor.py) | Prompt, tool loop, lockfile tool, integrity guard, escalation, case files |
| [`beam.py`](beam.py) | Reflection API client with the budget guard and key rotation |
| [`migration_notes.md`](migration_notes.md) | Hints given to Beam, to verify against the logs |
| [`gpu_run.py`](gpu_run.py) | The same loop for GPU Spaces on an NVIDIA A10G |

**Next:** [06 · Verify and review →](../06_verify_and_review)
