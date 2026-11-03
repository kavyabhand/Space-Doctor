# 03 · Census and triage

> Beam read every public error log of the broken Spaces in a single call.

## Census

[`harvest.py`](harvest.py) pages through the Hub API (`/api/spaces?sort=likes`) for the 10,000 most-liked Spaces
and fetches each broken Space's public runtime error. Result: 3,513 broken, with a public error message for 3,393.

## One-call triage

[`triage.py`](triage.py) cleans each log (strips ANSI codes and progress bars, keeps the last 600 characters) and
sends all 3,393 to Beam at once: **403,063 input tokens, answered in 70 seconds**. Beam returns root-cause
families, each with a Python regex, a typical fix and whether it is fixable in code.

**We do not take Beam's word for the counts.** The script runs every regex over every log itself and records what
each one actually matches.

## A second pass, and a metric Beam padded

[`triage_refine.py`](triage_refine.py) shows Beam only the logs its first taxonomy missed (122,343 tokens) and asks
for more families.

| | Coverage of the 3,393 logs |
|---|---|
| After the first call | 60% |
| After the second call, as measured | 90% |
| **Without the catch-all regex** | **67%**: the figure we report |

The jump to 90% came mostly from one new "family" whose regex matched almost anything
(`Exit code:|Reason:|Space failed|...`, 765 logs). Code measured the regexes, so we could see it. We treat any
regex matching 20% or more of all logs as a catch-all, and leave it out of the specific count.

## What the causes look like

The largest specific families: scheduler or hardware capacity (290, platform), build failures (261), launch
timeouts (191, platform), ZeroGPU torch incompatibility (181), missing Python dependencies (151), removed
`huggingface_hub` APIs, gradio API drift. Full table: [`triage.json`](triage.json).

| File | What it is |
|---|---|
| [`harvest.py`](harvest.py) | Census of the most-liked Spaces |
| [`triage.py`](triage.py) | One Beam call over every error log, regexes measured by code |
| [`triage_refine.py`](triage_refine.py) | Second pass over the logs the first missed |
| [`triage.json`](triage.json) | Families, regexes, measured counts, likes per family |

**Next:** [04 · Reproduce →](../04_reproduce)
