# 07 · Baseline: does it take a model?

> The obvious alternative is free. So we ran it.

## Time-travel pinning

[`baseline.py`](baseline.py) rebuilds each untouched broken Space with **every dependency resolved as it existed on
the day of the Space's last commit** (`uv pip install --exclude-newer <lastModified>`), on Python 3.10 unless the
README pins another version. Same rebuild, same probes, same definition of revived.

## Result

| On 204 patients run both ways | Spaces |
|---|---|
| **Revived by Beam** | **30** |
| Revived by the baseline | 9 |
| Revived by Beam only | 28 |
| Revived by the baseline only | 7 |
| Revived by both | 2 |
| Revived by neither | 167 |

Pinning the past fixes some Spaces, and we show the 7 that only the baseline revived rather than hide them. But
most broken Spaces need more than a date: a removed gradio call to migrate, a lockfile date that satisfies the
Space's own explicit pins, a dependency that must be added or dropped, a model download that moved. That is the
judgement Beam supplies.

**Next:** [08 · Results →](../08_results)
