"""Save the full wikitext of a 'Visa requirements for X citizens' page as a test fixture."""
import json
import sys
import time
from pathlib import Path

import requests

API = "https://en.wikipedia.org/w/api.php"
UA = "VisaApp-DataPipeline/0.1 (https://github.com/Riedel-David/Visa-requirements)"
OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def fetch(title: str) -> None:
    r = requests.get(API, params={
        "action": "parse", "page": title, "prop": "wikitext|revid", "redirects": 1,
        "format": "json", "formatversion": 2, "maxlag": 5,
    }, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    p = r.json()["parse"]
    slug = p["title"].replace(" ", "_")
    (OUT / f"{slug}.wikitext").write_text(p["wikitext"], encoding="utf-8")
    (OUT / f"{slug}.meta.json").write_text(json.dumps({"title": p["title"], "revid": p["revid"]}, indent=2) + "\n")
    print(slug, p["revid"], len(p["wikitext"]))


if __name__ == "__main__":
    for t in sys.argv[1:]:
        fetch(t)
        time.sleep(1)
