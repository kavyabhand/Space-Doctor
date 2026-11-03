---
title: Space Doctor
emoji: 🩺
colorFrom: green
colorTo: gray
sdk: static
pinned: true
license: apache-2.0
short_description: Beam revives broken HF Spaces, verified by calling their API
tags:
  - beam
  - reflection-ai
  - build-with-beam
  - agents
  - code-repair
  - long-context
  - huggingface-spaces
  - verification
  - hackathon
---

<p align="center">
  <img src="assets/banner.png" width="100%" alt="Space Doctor" />
</p>

<h1 align="center">Space Doctor</h1>

<p align="center"><b>Every Space deserves a second life.</b></p>

<p align="center">
  ${broken_pct} of the 10,000 most-liked Hugging Face Spaces no longer run. Space Doctor gives each one to
  <a href="https://huggingface.co/reflection/Beam-1.0-501B-A23B">Beam</a>, Reflection AI's open 501B model, to diagnose and repair,
  then rebuilds the Space and calls its API. A repair only counts if a real answer comes back.
</p>

<p align="center"><i>Made by ${authors_html} for the Build with Beam challenge</i></p>

<p align="center">
  <a href="https://huggingface.co/reflection/Beam-1.0-501B-A23B"><img src="https://img.shields.io/badge/Model-Beam--1.0--501B--A23B-0a8fb3?style=flat-square" alt="Model: Beam" /></a>
  <a href="https://huggingface.co/datasets/${hf_user}/spacerot"><img src="https://img.shields.io/badge/Dataset-SpaceRot-FFD21E?style=flat-square&logo=huggingface&logoColor=black" alt="Dataset: SpaceRot" /></a>
  <a href="https://github.com/kavyabhand/Space-Doctor"><img src="https://img.shields.io/badge/Code-GitHub-181717?style=flat-square&logo=github&logoColor=white" alt="Code: GitHub" /></a>
  <a href="#results"><img src="https://img.shields.io/badge/Revived_%26_verified-${revived}_Spaces-0a8fb3?style=flat-square" alt="Revived and verified" /></a>
  <a href="#pull-requests"><img src="https://img.shields.io/badge/Pull_requests-${n_prs}_open-e0604d?style=flat-square" alt="Pull requests" /></a>
  <a href="https://huggingface.co/reflection/Beam-1.0-501B-A23B/discussions/5"><img src="https://img.shields.io/badge/Build_with_Beam-Reflection_×_Hugging_Face-111111?style=flat-square" alt="Build with Beam" /></a>
</p>

<p align="center"><video src="https://huggingface.co/spaces/kavyabhand/space-doctor/resolve/main/assets/demo.mp4" poster="https://huggingface.co/spaces/kavyabhand/space-doctor/resolve/main/assets/demo_poster.jpg" controls muted playsinline width="100%"></video></p>
<p align="center"><sub>The film: 90 seconds, narrated</sub></p>

---

## Submission Snapshot

| | |
|---|---|
| **Live gallery** | This Space: every revival, its patch, and what the revived app returned |
| **Dataset** | [${hf_user}/spacerot](https://huggingface.co/datasets/${hf_user}/spacerot): census of 10,000 Spaces, ${treated} case files, all Beam traces, the pipeline code |
| **Demo video** | [90-second narrated film](https://huggingface.co/spaces/kavyabhand/space-doctor/resolve/main/assets/demo.mp4) |
| **Code** | [github.com/kavyabhand/Space-Doctor](https://github.com/kavyabhand/Space-Doctor), told as twelve chapters |
| **Model** | [`reflection/Beam-1.0-501B-A23B`](https://huggingface.co/reflection/Beam-1.0-501B-A23B) via Reflection's API, `reasoning_effort` medium → high |
| **What Beam does** | Reads 3,393 error logs in one call to find why Spaces die; reads a whole broken Space to write its repair; decides when a Space can't honestly be fixed |
| **Verifier** | Rebuild with the Spaces recipe, then call the app's main endpoint. Only a real, non-empty result counts |
| **Pull requests** | ${n_prs} opened on revived Spaces, each after human review ([list](#pull-requests)) |
| **Made by** | ${authors} |

---

## The Idea

Open a Hugging Face Space from 2023 and there is a good chance you get a red **Runtime error** instead of a demo.
On ${census_date} we checked the **10,000 most-liked Spaces: ${broken} were broken (${broken_pct}), holding
${broken_likes} likes.** GFPGAN, XTTS, AudioLDM, ControlNet: demos people loved, now dead.

Most of them did nothing wrong. Spaces reinstall unpinned dependencies on every rebuild, so code that worked
when it shipped now meets gradio 5 and 6, `huggingface_hub` 1.0, numpy 2, torch 2.6 and Python 3.13. The fix is
usually small. Finding it means reading the repo, the traceback and the package versions together, which is
work nobody does for a Space they abandoned two years ago.

**Space Doctor** gives that work to Beam, and then refuses to believe Beam until the Space actually runs.

---

## What It Does

```
10,000 most-liked Spaces          Hub API: status + public error log of each
        |
${broken} broken                  runtime / build / config errors
        |
Triage (1 Beam call, ${triage_tokens} tokens)   Beam reads every error log at once and proposes root-cause
        |                           families as regexes; code runs them and measures coverage
Reproduce (${repro_attempted} rebuilt)          the untouched Space must still fail in our Spaces-like rebuild
        |
Diagnose + patch (Beam)           whole repo + HF's log + our log + resolved packages + build recipe
        |                           -> JSON patch, a dated lockfile, or "unfixable"
Inner loop (no rebuild)           patch doesn't apply / lock doesn't resolve / file not shown -> straight back to Beam
        |
Integrity guard                   reject patches that delete code, drop functions, add blanket excepts, change SDK
        |
Rebuild + call the API            the Space must boot and its main endpoint must return a real result
        |                           failed? back to Beam with the new logs, at higher reasoning effort
${revived} revived, ${likes_revived} likes back      each with a verified patch, ready as a PR for its owner
```

---

## Results

| | |
|---|---|
| Spaces checked | ${spaces} (top by likes, ${census_date}) |
| Broken | **${broken}** (${broken_pct}), ${broken_likes} likes |
| Rebuilt by us, still broken today | ${still_broken} of ${repro_attempted} (${same_exc} fail with exactly HF's exception) |
| Treated by Beam | ${treated} (${gpu_cases} on an NVIDIA A10G) |
| **Revived and verified** | **${revived}**, ${likes_revived} likes |
| Boots, inference unverified | ${api_tier} |
| Beam: "unfixable" | ${unfixable} (gated or private models, owner-only secrets, dead download links) |
| Passed every check, rejected at human review | ${rejected} (the patch gamed the verifier; see [Honesty](#honesty-where-beam-could-have-cheated)) |
| Not revived | ${failed} |

${highlights}

The gallery shows each one side by side: the error Hugging Face shows today, and what the repaired app returned.

---

## Pull Requests

Every verified revival that a person approved went back to its owner as a pull request on the original Space:
only the changed files, plus the error, Beam's diagnosis, how we tested it and what the app returned.

${prs_table}

---

## How Beam Is Used

| Step | What Beam does | Why it needs Beam |
|---|---|---|
| **Triage** | Reads the error logs of all ${triage_logs} broken Spaces in **one call (${triage_tokens} input tokens, ${triage_secs}s)** and proposes failure families as regexes. A second call sees only the logs the first missed. | Long context: the whole failure landscape at once, not a sample |
| **Diagnosis** | Gets the full repo (most relevant files first), HF's log, our rebuild log, the exact `pip freeze` and the Dockerfile Spaces will use. Cites the decisive log line. | Long-context code reasoning across files and logs |
| **Repair strategy** | Chooses per Space: a minimal code edit that keeps it on today's libraries, a **dated lockfile** (`uv pip compile --exclude-newer <date Beam picks>`), or both | Judgement, not a rule: ${lock_used} of ${revived} revivals used a lockfile |
| **Tool loop** | Asks for files it wasn't shown (`need_files`); gets patch and lock errors back instantly, before any rebuild | Agentic repair with cheap checks before expensive ones |
| **Escalation** | `reasoning_effort` medium; high only after a failed rebuild, with the new logs | ${fixed_at} |
| **Token efficiency** | A median of **${median_reasoning} reasoning tokens per repair call** and ${out_per_revived_median} output tokens to revive a Space (median, every attempt counted). The whole triage took ${triage_reasoning} reasoning tokens over ${triage_tokens} tokens of logs | Beam's headline strength, measured on real repairs |
| **Abstention** | May answer `"verdict": "unfixable"`, and did ${unfixable} times | An honest "no" is worth more than a fake fix; we checked every one by hand |

---

## Does It Take a Model?

The obvious alternative is free: rebuild each Space with every dependency as it existed on its last commit
(`uv pip install --exclude-newer <lastModified>`, Python 3.10 unless pinned), with the same verifier.

| | Spaces |
|---|---|
| Revived by Beam only | **${beam_only}** |
| Revived by the time-travel baseline only | ${baseline_only} |
| Revived by both | ${both} |
| Revived by neither | ${neither} |

${baseline_note}

---

## Honesty: Where Beam Could Have Cheated

Any model graded by an automatic check can learn to pass the check instead of doing the task. Here is everywhere
that could have happened in this project, and what the logs show.

- **"Unfixable" ${unfixable} times instead of faking a fix.** CodeGeeX needs the owner's paid API key (Beam still
  named the Python 3.13 `audioop` fix so the owner can apply it). Every-Text loads its whole app from a secret.
  Real-Time-Voice-Cloning's weights sit behind a dead Google Drive link. We read every one against the logs.
- **${rejected} patches passed every automatic check and were still rejected at review.** We read every revival before
  counting it. One rewrote each `<|endoftext|>` in the app as junk text, apparently because the model cannot emit
  that special token. Others loosened an app's input check, returned placeholder messages, handed back the input
  image unchanged, or only stopped an API-key error from crashing. Each made our probe pass without making the app
  work. None is counted, and a guard now rejects the special-token case automatically. ${unverified_rev} more were
  downgraded to "boots, unverified" because their output did not show the app working.
- **A check we made stricter caught a false positive.** Streamlit apps have no API to call, so "boots" was all we
  could check at first. We added a browser render check that requires visible content and no error box. It
  immediately downgraded one "revived" Space whose page showed a model-loading error.
- ${guard_line}
- **Beam padded a metric when it could.** Asked to cover the logs its first triage missed, it added a catch-all
  regex that matches ${catch_all} logs. Coverage "rose" to ${cov_reported}; specific coverage is **${cov_specific}**,
  the number we report. Code measured it, which is the only reason we know.
- **Beam edited files it had not seen.** Early runs fed files alphabetically, and in big repos Beam "quoted"
  `requirements.txt` lines it was never shown. We now show the relevant files first, list the rest by name, and
  let Beam ask for them. Every remaining bad quote is caught before a rebuild (${bad_edits} times in total).
${empty_line}
---

## Cost

| | |
|---|---|
| Beam calls (triage + repair) | ${calls} |
| Input tokens | ${prompt_tokens} (${cached_pct} served from Reflection's prompt cache) |
| Output tokens | ${completion_tokens} (${out_per_revival} per revival, failures included) |
| Reasoning tokens per repair call | ${median_reasoning} (median) |
| Output tokens to revive one Space | ${out_per_revived_median} (median, every attempt counted) |
| Median Beam call | ${median_call}s |
| Median end-to-end per Space | ${median_wall} min, almost all of it Docker builds |

All on Reflection's free API tier.

---

## Try It

**The gallery** is this Space. Every card links to its case file: diagnosis, patch, all attempts, and the output.

**Fix your own Space** (needs Docker and a free key from [platform.reflection.ai](https://platform.reflection.ai)):

```bash
pip install huggingface_hub gradio_client requests pyyaml uv
export REFLECTION_API_KEY=...
git clone https://github.com/kavyabhand/Space-Doctor && cd Space-Doctor
python 11_tools_for_owners/cli.py owner/your-space      # reproduce -> Beam patch -> rebuild -> call the API
python 11_tools_for_owners/open_pr.py spacedoctor_runs/owner__your-space --go   # only if verified and approved
```

**Re-run the whole study:** every command, machine and cost is in
[chapter 12 on GitHub](https://github.com/kavyabhand/Space-Doctor/tree/main/12_run_it_yourself).

---

## Technical Notes

**Reproduce before you repair.** A Space is only a patient if our rebuild of the untouched repo fails today.
${transient} Spaces that Hugging Face shows as broken started fine for us (an upstream API returning 429, a
transient build failure); they were left alone.

**A Spaces-like rebuild.** README front-matter (`python_version`, `sdk_version`), `packages.txt`,
`requirements.txt`, then the SDK and `spaces` installed after it, as Spaces does. That order matters: an SDK
install can silently re-upgrade a pin Beam just added, so Beam is shown the Dockerfile. CPU Spaces build with CPU
torch wheels (same Python API) under cpu-basic limits (2 vCPU, 16 GB). GPU Spaces ran on an NVIDIA A10G.

**What "functional" means.** The probe reads the app's API schema, picks the main endpoint (not a clear button
or example loader), and calls it with gradio's own schema-valid example input, using the Space's own example
image or audio file when it ships one. The result must be non-empty, and returned files must exist and be
non-empty. It is a smoke test, not a quality grade, so the outputs are shown for you to judge.

**Patches are PR-ready.** Edits preserve each file's line endings. The README pins the `python_version` we
verified with, so the environment that deploys is the one we tested.

**Untrusted code.** Thousands of strangers' apps ran on our machines: no cloud credentials on the instances, and
containers blocked from the instance metadata service.

---

## Submission Compliance

| Requirement | Status | Evidence |
|---|---|---|
| Public Hub repo | ✅ | This Space + the [SpaceRot dataset](https://huggingface.co/datasets/${hf_user}/spacerot) |
| README explains how Beam is used | ✅ | [How Beam Is Used](#how-beam-is-used) |
| Uses Beam | ✅ | `Beam-1.0-501B-A23B`, ${calls} calls, every trace in the dataset |
| Shared in the challenge thread | ✅ | [discussion #5](https://huggingface.co/reflection/Beam-1.0-501B-A23B/discussions/5) |

---

## Judging Criteria

| Criterion | Why Space Doctor fits |
|---|---|
| **Creativity & originality** | Nobody repairs the Hub's own graveyard. The target is Hugging Face itself, and the result is visible in one sentence |
| **Technical execution** | Reproduce-first, a Spaces-faithful rebuild, an API-level verifier, an integrity guard, a no-LLM baseline, and every failure published |
| **Usefulness & impact** | ${broken} broken Spaces, ${broken_likes} likes. Verified patches go to owners as PRs; any owner can run the CLI on their own Space |
| **Innovative use of Beam** | 1M-context triage over every error log, whole-repo diagnosis, Beam choosing between modernizing code and pinning an era, a tool loop, effort escalation, and honest abstention, measured |

---

## Project Layout

The full code, told as twelve chapters (problem → idea → census → reproduce → repair → verify → baseline →
results → honesty → gallery → tools → run it yourself), is on
**[GitHub: kavyabhand/Space-Doctor](https://github.com/kavyabhand/Space-Doctor)**. This Space holds:

```
.
├── index.html             The gallery (static, no server)
├── data/                  summary.json, triage.json, cases.json, census_min.json, outputs/ (what revived apps returned)
├── assets/banner.png
└── code/
    ├── harvest.py         Census of the 10,000 most-liked Spaces
    ├── triage.py          One Beam call over every error log; regexes measured by code
    ├── triage_refine.py   Second pass over the logs the first one missed
    ├── reproduce.py       Rebuild untouched Spaces with the Spaces recipe; keep the ones still broken
    ├── sandbox.py         Spaces-like Docker build, boot, API probe
    ├── probe.py           Calls the main endpoint with schema-valid inputs, inside the app's container
    ├── probe_legacy.py    The same for gradio 3.x apps (websocket queue protocol)
    ├── probe_streamlit.py Browser render check for Streamlit apps
    ├── doctor.py          Beam repair loop: context, tool turns, lockfile tool, integrity guard, escalation
    ├── gpu_run.py         The same loop on an NVIDIA A10G
    ├── baseline.py        No-LLM time-travel baseline
    ├── reprobe.py         Stricter re-checks of every revival, no Beam calls
    ├── review_queue.py    Flags what a person must still read
    ├── reviews.json       Every human verdict, with its reason
    ├── beam.py            Reflection API client with a daily-budget guard
    ├── cli.py             Fix one Space on your own machine
    ├── open_pr.py         Open a PR for a verified, approved fix only
    └── report.py, export_gallery.py, fill_readme.py
```

---

<div align="center">

*Every Space deserves a second life.*

**Made with 🩺 by ${authors}**

</div>
