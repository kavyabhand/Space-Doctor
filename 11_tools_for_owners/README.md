# 11 · Tools for owners

> If your Space shows a runtime error, you can run the same verified loop on it yourself.

## Fix one Space

```bash
pip install -r requirements.txt          # and Docker with buildx
export REFLECTION_API_KEY=...            # free key from platform.reflection.ai
python 11_tools_for_owners/cli.py owner/your-space
```

[`cli.py`](cli.py) fetches the Space, reproduces the failure in a Spaces-like rebuild, lets Beam diagnose and patch
it, rebuilds, and calls the app. It writes `spacedoctor_runs/<owner>__<space>/` with `repro.json`, `case.json`
(every attempt, diff and probe result) and `fixed/`. Nothing is pushed anywhere.

GPU Space: set `SD_GPU=1` on a machine with an NVIDIA GPU.

## Propose the fix

```bash
python 11_tools_for_owners/open_pr.py spacedoctor_runs/owner__your-space          # preview only
python 11_tools_for_owners/open_pr.py spacedoctor_runs/owner__your-space --go     # open the PR
```

[`open_pr.py`](open_pr.py) refuses unless the case reached the verified tier **and** has an approved review in
`06_verify_and_review/reviews.json`, and only if the Space is still broken on Hugging Face. The PR contains only
the changed files, plus the error, Beam's diagnosis, how it was tested and what the app returned.

**Next:** [12 · Run it yourself →](../12_run_it_yourself)
