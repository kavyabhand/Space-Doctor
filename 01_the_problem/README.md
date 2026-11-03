# 01 · The problem

> A third of the most-liked demos on Hugging Face show a red **Runtime error** instead of running.

## What we measured

On 2026-10-30 we read the status and public error log of the **10,000 most-liked Spaces** from the Hub API
([`03_census_and_triage/harvest.py`](../03_census_and_triage/harvest.py)).

| Status | Spaces |
|---|---|
| Running | 4,854 |
| Paused or sleeping | 1,632 |
| **Runtime error** | **2,755** |
| **Build error** | **545** |
| **Config error** | **213** |
| **Broken in total** | **3,513 (35%)**, holding **211,237 likes** |

These are not obscure experiments. The broken list includes coqui/xtts (2,764 likes), Xintao/GFPGAN, DragGan,
Meta's MMS, Stability AI's StableLM 2 chat demo and Microsoft's speaker-verification demos.

## Why they die

Most of these Spaces did nothing wrong. A Space reinstalls its dependencies every time it rebuilds, and most
`requirements.txt` files are unpinned. So code that worked when it shipped now meets:

- **gradio 4, 5 and 6**, which removed `gr.inputs`, `enable_queue`, `allow_flagging`, `.style()` and more
- **`huggingface_hub` 1.0**, which removed `HfFolder` and `cached_download` (and old gradio imports them)
- **numpy 2**, which breaks extensions built for numpy 1 and removed aliases like `np.bool8`
- **torch 2.6**, whose `torch.load(weights_only=True)` default rejects old checkpoints
- **Python 3.13**, which removed the `audioop` module that gradio's audio stack imports
- **torchvision 0.17**, which removed the module `basicsr` (GFPGAN, Real-ESRGAN) imports

The fix is usually small. Finding it means reading the repo, the traceback and the installed package versions
together. Nobody does that work for a demo they shipped two years ago.

## Not every broken Space is fixable in code

Some failures belong to the platform (no GPU capacity, storage quota, launch timeouts) or to the owner (a missing
API key, a private model). Part of the job is telling these apart honestly. [Chapter 03](../03_census_and_triage)
shows how Beam sorted all 3,393 public error logs into causes.

**Next:** [02 · The idea →](../02_the_idea)
