"""Census of the most-liked Hugging Face Spaces: which are broken, and why (public runtime error)."""
import sys, pathlib; _ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path[:0] = [str(p) for p in sorted(_ROOT.glob("[0-9][0-9]_*"))]  # chapters import each other
import json, sys, time, concurrent.futures as cf
import requests

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
OUT = sys.argv[2] if len(sys.argv) > 2 else "/data/census.json"
BROKEN = {"RUNTIME_ERROR", "BUILD_ERROR", "CONFIG_ERROR"}
S = requests.Session()

url = ("https://huggingface.co/api/spaces?limit=1000&sort=likes&direction=-1"
       "&expand[]=runtime&expand[]=sdk&expand[]=likes&expand[]=lastModified")
rows = []
while url and len(rows) < N:
    r = S.get(url, timeout=60)
    r.raise_for_status()
    for s in r.json():
        rt = s.get("runtime") or {}
        rows.append({"id": s["id"], "likes": s.get("likes", 0), "sdk": s.get("sdk"),
                     "stage": rt.get("stage"), "hw": (rt.get("hardware") or {}).get("requested"),
                     "err": rt.get("errorMessage"), "lastModified": s.get("lastModified")})
    url = r.links.get("next", {}).get("url")
rows = rows[:N]


def err_for(row):
    for attempt in range(5):
        r = S.get(f"https://huggingface.co/api/spaces/{row['id']}/runtime", timeout=30)
        if r.status_code == 429:
            time.sleep(2 + attempt * 3)
            continue
        if r.ok:
            row["err"] = r.json().get("errorMessage")
        return row
    row["err"] = "FETCHFAIL"
    return row


need = [r for r in rows if r["stage"] in BROKEN and not r["err"]]
with cf.ThreadPoolExecutor(4) as ex:
    list(ex.map(err_for, need))
json.dump(rows, open(OUT, "w"))
from collections import Counter
print(len(rows), Counter(r["stage"] for r in rows).most_common())
