# 06 · Verify and review

> "It boots" is not a revival. The app has to answer, and a person has to agree.

## 1. Integrity guard (before any rebuild)

In [`../05_repair_with_beam/doctor.py`](../05_repair_with_beam/doctor.py), a patch is rejected if it:

- shrinks the app's Python code by more than 15%, or removes any function;
- adds more than one new `except` clause to the app file;
- changes the SDK;
- changes how often special-token text like `<|endoftext|>` appears (added after we caught Beam corrupting it; see
  [chapter 09](../09_honesty)).

## 2. Rebuild and call the app

The patched Space is rebuilt with the Spaces recipe and must boot. Then the probe calls its **main endpoint**, not
a clear button, example loader or seed randomizer, with a real input: the Space's own example file when it ships
one. The result must be non-empty, and any returned file must exist and be non-empty. Outputs are saved for review.

Gradio has changed its client protocol several times, so there are three probes:

| Probe | For |
|---|---|
| [`probe.py`](probe.py), run **inside the app's container** with the app's own `gradio_client` | gradio 3.19 and later; uses the schema's own example inputs |
| [`probe_legacy.py`](probe_legacy.py), speaking the old websocket queue protocol directly | gradio 3.x apps older than `gradio_client` |
| [`probe_streamlit.py`](probe_streamlit.py), a headless browser render check | Streamlit apps, which have no API: content must render with no error box |

[`reprobe.py`](reprobe.py) re-runs a stricter check on an existing patch without calling Beam again, and records
both the old and new results.

## 3. A person reviews every revival

[`review_queue.py`](review_queue.py) lists unreviewed revivals and flags risky ones: code changes beyond pins,
added fallbacks or loosened checks, outputs that look like error messages or echo the input. Every revival was read
by hand. Verdicts live in [`reviews.json`](reviews.json), each with a reason:

| Verdict | Count | Meaning |
|---|---|---|
| approved | 34 | counted as revived |
| unverified | 7 | the app boots, but the output does not show it working |
| rejected | 6 | passed every automatic check and is still wrong; not counted |

Where a fair test needed a fair input, we re-ran it and say so in the review. For example, the medical
de-identification model was re-tested on a realistic note (it tagged PATIENT, DATE, HOSPITAL, STAFF and PHONE),
and Meta's MMS was re-run with Burmese selected for its Burmese clip (it returned a Burmese transcript).

**Next:** [07 · Baseline →](../07_baseline)
