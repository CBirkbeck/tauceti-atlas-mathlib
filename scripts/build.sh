#!/usr/bin/env bash
# Build the experiment: tauceti-explorer at the commit in UPSTREAM, with this repository's src/,
# scripts/, data/ and tests/ laid over it, then both pages (the atlas, and Tau Ceti's roadmaps alone)
# copied back here for GitHub Pages.
#
# tauceti-explorer is checked out as a worktree of a local clone (TAUCETI_EXPLORER, by default
# ~/GitHub/tauceti-explorer) in .upstream/, which this script resets on every run: never edit there.
#
#   scripts/build.sh            lay over and build both pages
#   scripts/build.sh --overlay  only lay over (to run tests in .upstream/)
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
live=${TAUCETI_EXPLORER:-$HOME/GitHub/tauceti-explorer}
up="$here/.upstream"
commit=$(tr -d '[:space:]' < "$here/UPSTREAM")

if [ ! -e "$up/.git" ]; then
  git -C "$live" cat-file -e "$commit^{commit}" 2>/dev/null || git -C "$live" fetch -q origin
  git -C "$live" worktree add -q --detach "$up" "$commit"
fi
# Back to tauceti-explorer exactly as it was at UPSTREAM, then this repository over it.
git -C "$up" checkout -q --detach "$commit"
git -C "$up" reset -q --hard "$commit"
git -C "$up" clean -fdq
git -C "$here" ls-files -z -- src scripts data tests | while IFS= read -r -d '' path; do
  mkdir -p "$up/$(dirname "$path")"
  cp "$here/$path" "$up/$path"
done
# Files added here but not yet committed take part too, so a build can be checked before it is committed.
git -C "$here" ls-files -z --others --exclude-standard -- src scripts data tests | while IFS= read -r -d '' path; do
  mkdir -p "$up/$(dirname "$path")"
  cp "$here/$path" "$up/$path"
done
[ "${1:-}" = "--overlay" ] && { echo "laid over tauceti-explorer ${commit:0:12} in $up"; exit 0; }

(cd "$up" && python3 scripts/build.py > /dev/null && python3 scripts/build.py --tauceti > /dev/null)
mkdir -p "$here/tauceti"
cp "$up/index.html" "$here/index.html"
cp "$up/BUILD.json" "$here/BUILD.json"
cp "$up/tauceti/index.html" "$here/tauceti/index.html"
cp "$up/tauceti/BUILD.json" "$here/tauceti/BUILD.json"
ls -la "$here/index.html" "$here/tauceti/index.html"
