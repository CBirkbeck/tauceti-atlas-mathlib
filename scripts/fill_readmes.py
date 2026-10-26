#!/usr/bin/env python3
"""Fill the cache of proposed roadmaps' READMEs (data/tauceti-prs-readmes.json, which tauceti-explorer keeps out of
its repository) for the pull requests data/tauceti-prs.json lists at UPSTREAM, each read at the commit recorded there.
Unlike `scripts/tauceti_prs.py --fetch`, it does not ask GitHub for the pull requests again, so the experiment shows
the roadmaps as they were at UPSTREAM; it reads only raw files, which the API's rate limit does not count."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from tauceti_prs import CACHE, COPY, cached, raw  # noqa: E402


def main() -> int:
    data = json.loads(COPY.read_text(encoding="utf-8"))
    readmes = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    pulls = {pull["number"]: pull for pull in data.get("pulls", [])}
    wanted = {cached(pulls[entry["pull"]], folder): (pulls[entry["pull"]], folder)
              for folder, entry in data.get("roadmaps", {}).items() if entry["pull"] in pulls}
    missing = [key for key in wanted if key not in readmes]

    def read(key):
        pull, folder = wanted[key]
        return key, raw({"headRepository": {"nameWithOwner": pull["head"]}, "headRefOid": pull["sha"]}, folder + "/README.md")

    with ThreadPoolExecutor(max_workers=8) as pool:
        for key, text in pool.map(read, missing):
            if text is not None:
                readmes[key] = text
    CACHE.write_text(json.dumps({key: readmes[key] for key in wanted if key in readmes}, ensure_ascii=False) + "\n", encoding="utf-8")
    still = [key for key in wanted if key not in readmes]
    print(f"{len(wanted) - len(still)} of {len(wanted)} proposed READMEs cached ({len(missing) - len(still)} read now)")
    return 1 if still else 0


if __name__ == "__main__":
    sys.exit(main())
