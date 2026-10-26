# Tau Ceti Atlas with a Mathlib disk (experiment)

An experimental version of the [Tau Ceti atlas](https://cbirkbeck.github.io/tauceti-explorer/). It opens the same as the
live atlas: Mathlib is the small sun at the centre, inside an empty circle, with the roadmaps' sectors round it. Hover over
the sun and the Mathlib disk opens a little; click it and the disk opens fully round the sun. Click the sun again and the
disk closes back into the live view.

The disk is divided into the same arXiv areas as the map. On it are Mathlib's key definitions and theorems:
- the 913 its own catalogues name (`docs/overview.yaml`, `docs/undergrad.yaml`, `docs/100.yaml`, `docs/1000.yaml`), titled in their words;
- as the camera closes in, 8,016 main definitions and results that its files list in their headers.

Each item lies as far from the centre as the number of Mathlib definitions needed to state and prove it, on a logarithmic
scale. The deepest declaration of Mathlib needs 6,564. Clicking an item opens its statement, what it needs, and links to
Mathlib's docs and source.

The disk and the map share one division: the disk's slices are the map's sectors, and each sector's share counts its
roadmaps and Mathlib's items in it, half each, so a dividing line runs straight from the sun to the map's edge. Mathlib
has material in five areas that have no roadmaps yet: Rings and Algebras, General Topology, Dynamical Systems, Spectral
Theory and Statistics Theory. Their slices are on the map, empty outside until roadmaps come. So the map's sectors
differ from the live atlas's: number theory's narrow, and algebra, topology and analysis widen.

The disk is a first pass. Where Mathlib's folders go (`data/mathlib-areas.json`) is a table to edit.

**[Open the experiment](https://cbirkbeck.github.io/tauceti-atlas-mathlib/)** · [Tau Ceti's roadmaps alone](https://cbirkbeck.github.io/tauceti-atlas-mathlib/tauceti/)

Since 26 October 2026 the disk is on the live atlas: tauceti-explorer took it in commit 38daa2a26, with its scheduled
update making the disk again whenever Tau Ceti's Mathlib commit moves (`scripts/mathlib_refresh.sh` there). This
repository stays as a place to try the next changes before they go live; nothing here changes the live atlas.

## How it is built

This repository holds only what the experiment changes or adds, at the paths it has in tauceti-explorer, laid over
tauceti-explorer at the commit in `UPSTREAM`:

    scripts/build.sh      # lays this repository over tauceti-explorer at UPSTREAM and builds both pages

The roadmaps, their progress and every other input come from tauceti-explorer at that commit, so the experiment shows the
roadmaps as they were then. Move `UPSTREAM` forward and rebuild to bring them up to date.

## Mathlib's data

`.github/workflows/mathlib-dataset.yml` runs the extractor the Tau Ceti review site uses (trust-extract) with Mathlib itself
as the library, at the Mathlib commit in `data/mathlib-pin.json`, and publishes the dataset as a release.
`scripts/mathlib_disk.py` reads it, with Mathlib's catalogues and file headers, and writes `data/mathlib-disk.json`.
