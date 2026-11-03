# 02 · The idea

> Give the repair to Beam. Then refuse to believe Beam until the Space actually runs.

## In one picture

```
10,000 most-liked Spaces ──► census of status + public error logs                 (03)
          │
     3,513 broken ──► Beam reads every error log in one call, names the causes      (03)
          │
   rebuild each untouched Space the way Spaces does ──► it must still fail          (04)
          │
   Beam gets the whole picture in one prompt ──► patch · dated lockfile · "unfixable"   (05)
          │         ▲
          │         └── patch doesn't apply, lockfile doesn't resolve, file not shown:
          │             straight back to Beam, in seconds, no rebuild
          ▼
   integrity guard ──► rebuild ──► call the app's main endpoint with a real input  (06)
          │         ▲
          │         └── failed? back to Beam with the new logs, at higher effort
          ▼
   a person reviews every revival ──► pull request to the owner                    (06, 11)
```

## The rules we held ourselves to

1. **Reproduce first.** A Space is only a patient if our rebuild of the untouched repo fails today.
2. **Verify by calling the app.** "It boots" is not enough. The main endpoint must return a non-empty result for
   a real input, preferably the Space's own example file.
3. **No gutting.** A patch that deletes code, drops functions, swallows errors or changes special-token text is
   rejected before it is rebuilt.
4. **Abstaining is allowed.** If a Space cannot be fixed honestly (an owner-only key, a gated model, a dead
   download), the right answer is "unfixable", and Beam is told so.
5. **A person reads every revival.** Passing every automatic check is necessary, not sufficient (see
   [chapter 09](../09_honesty) for why).
6. **Measure, don't claim.** Every number in this repo comes from a file you can open.
7. **Owners decide.** We only open pull requests for verified, reviewed fixes, and never change anyone's Space.

## Why Beam

- **Long context.** One call reads 3,393 error logs. One prompt holds a whole repository, its logs, the resolved
  package set and the build recipe.
- **Agentic coding.** It plans a fix, uses tools (ask for files, request a dated lockfile) and revises from
  feedback.
- **Calibration.** It can say "I can't fix this honestly" instead of producing something that merely runs.
- **Open weights, free API.** Anyone can rerun this study.

**Next:** [03 · Census and triage →](../03_census_and_triage)
