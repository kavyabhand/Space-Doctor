# 12 · Run it yourself

> Every number in this repo can be regenerated. Here is how, and what it cost.

## Machines we used

| Machine | For | Cost |
|---|---|---|
| AWS m7a.8xlarge (32 vCPU, 128 GB), Ubuntu 24.04 | CPU rebuilds, 20 Spaces in parallel | about $1.86/h |
| AWS g5.2xlarge, NVIDIA A10G (the GPU of HF's a10g-small) | GPU Spaces | about $1.21/h |
| A spot m6a.4xlarge | the no-model baseline (until reclaimed) | about $0.26/h |

Total compute for the study was about $50. Beam ran on Reflection's free daily allowance. Instances had no cloud
credentials, and containers were blocked from the metadata service.

## The pipeline, in order

```bash
# data lives in /data by default: census.json, repro/<owner>__<space>/{repro,case,baseline}.json
export REFLECTION_API_KEY=...                       # REFLECTION_API_KEY_2 is used when the first key's day is spent
python 03_census_and_triage/harvest.py 10000 /data/census.json
python 03_census_and_triage/triage.py /data/census.json /data/triage.json
python 03_census_and_triage/triage_refine.py /data/census.json /data/triage.json
python 04_reproduce/reproduce.py 240 6               # rebuild the top code-level failures
SD_WORKERS=20 python 05_repair_with_beam/doctor.py  # treat every still-broken patient
SD_GPU=1 python 05_repair_with_beam/gpu_run.py owner/space ...   # on the GPU machine
python 07_baseline/baseline.py                       # the no-model control
python 06_verify_and_review/reprobe.py               # stricter re-checks, no Beam calls
python 06_verify_and_review/review_queue.py /data    # what still needs a human
python 08_results/report.py /data
python 10_gallery/export_gallery.py /data 10_gallery/data
```

[`status.py`](status.py) prints progress and budget; [`show.py`](show.py) prints a case file.

## Settings worth knowing

| Variable | Meaning |
|---|---|
| `SD_WORKERS` | parallel Spaces |
| `SD_GPU=1` | build with CUDA wheels and run with `--gpus all` |
| `BEAM_RESERVE_OUT`, `BEAM_RESERVE_IN` | how much of each key's daily allowance to keep back |
| `SD_PROBE_TEXT`, `SD_PROBE_CHOICE` | override the probe's text input or dropdown choice for a fair re-test |

## Data

Every case file, Beam trace, patch and the census are published as the
[SpaceRot dataset](https://huggingface.co/datasets/kavyabhand/spacerot). Spaces change: re-run `reproduce.py`
before relying on a case.

**Back to:** [the start](../README.md)
