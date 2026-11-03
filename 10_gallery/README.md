# 10 · Gallery

> The results page, published as a static Hugging Face Space.

[`index.html`](index.html) is a single static page. It reads everything from [`data/`](data):

| Section | What it shows |
|---|---|
| Hero | All 10,000 Spaces as a field of dots, ordered by likes; broken ones coral, revived ones cyan and pulsing |
| Results | A grid of revived Spaces with live lifelines and output thumbnails; tap one for the error, diagnosis, patch and output |
| Method | The five checks, a flow from census to outcome, and a terminal replay of real repairs |
| Causes | Beam's triage as bubbles, and the 60% / 90% / 67% coverage story |
| Control | Beam against the time-travel baseline |
| Findings | Where Beam could have cheated |
| Cost | Calls, tokens and time |
| Appendix | Every patient, searchable, with full case files |

Open it locally with any static server:

```bash
cd 10_gallery && python -m http.server 8000     # then open http://localhost:8000
```

| File | What it is |
|---|---|
| [`export_gallery.py`](export_gallery.py) | Writes `data/` from the case files, reviews and pull requests |
| [`fill_readme.py`](fill_readme.py) + [`README_TEMPLATE.md`](README_TEMPLATE.md) | Renders the Space's README from the final numbers |

**Next:** [11 · Tools for owners →](../11_tools_for_owners)
