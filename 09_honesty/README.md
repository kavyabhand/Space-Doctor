# 09 · Honesty

> Any model graded by an automatic check can learn to pass the check instead of doing the task. Here is everywhere
> that could have happened in this project, where it did, and what caught it.

## It said "unfixable" instead of faking a fix: 71 times

Beam may answer that a Space can't be fixed honestly. It did so for owner-only API keys (CodeGeeX, where it still
named the Python 3.13 fix for the owner), apps loaded from a secret (Every-Text), gated or deleted models, and dead
download links (Real-Time-Voice-Cloning's weights on a dead Google Drive link). We read the verdicts against the
logs.

## Six patches passed every automatic check and were still wrong

Each made our probe pass without making the app work. All six were caught by reading the diff and the output;
none is counted.

| Space | What the patch did |
|---|---|
| m-ric/beam_search_visualizer | Rewrote every `<|endoftext|>` in the app as junk text (`cía`), apparently because the model cannot emit that special token. The app ran, so the probe passed, but its logic was broken. **A guard now rejects any patch that changes special-token text.** |
| pritish/BookGPT | Removed the app's PDF-only upload check so the probe's test file got through; the "result" was the app's own validation error. |
| akhaliq/GPEN | Deleted the app's example downloads and made it return the input image unchanged when no face is found, which is how the probe's faceless image "passed". |
| R1ckShi/FunClip | Added early returns of placeholder messages ("No state found."), so handlers returned something. |
| cerebras/chain-of-thought | The app needs Cerebras's API key (the output is a 401); the patch only stopped the error path from crashing. |
| ethanchern/Anole | Switched `launch()` to `share=True`; the app still answered with an error. |

Seven more were downgraded to "boots, unverified" because the output did not show the app working: a UI helper
answered instead of the model, a page was still loading, the app's own "model not found" message, an error page,
and so on. Every verdict and its reason is in
[`../06_verify_and_review/reviews.json`](../06_verify_and_review/reviews.json).

## It padded a metric when it could

Asked to cover the error logs its first triage missed, Beam added one regex that matches almost any failure.
Coverage appeared to rise from 60% to 90%. Code measured the regexes, so we report 67%
([chapter 03](../03_census_and_triage)).

## It quoted code it had not seen

In large repos, early runs fed files alphabetically and Beam "quoted" `requirements.txt` lines it had never been
shown. The fix: relevant files first, the rest listed by name, and a `need_files` tool. Every bad quote is caught
before a rebuild and sent back; Beam asked for files 14 times instead of guessing.

## Our own checks were wrong too, and we fixed them

- A boot-only check counted a Streamlit app as revived while its page showed a model-loading error. The browser
  render check caught it and downgraded it.
- Our first probe used the newest `gradio_client` against old servers and failed on protocol, not on the apps.
  Probing inside each app's own container fixed that; a legacy probe covers gradio 3.x apps older than the client.
- One probe called a seed randomizer and counted the number it returned. Helper events with only numeric or toggle
  outputs no longer count.

**Next:** [10 · Gallery →](../10_gallery)
