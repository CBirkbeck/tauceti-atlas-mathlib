# The Mathlib disk: design (2026-10-26)

## Intent

The live atlas puts Mathlib at the centre as a small sun, with an empty circle round it and the roadmaps beyond. The sun
says nothing about what Mathlib contains. The user asked for an experimental atlas, hosted apart from the live one, in
which Mathlib opens into a faint disk. The disk is divided by the map's areas and shows Mathlib's key definitions and
theorems, each as far from the centre as the amount of Mathlib needed to state and prove it. The roadmaps then visibly
continue the mathematics that the disk shows.

## Behaviour (the user's words: "the sun and empty disk we have now is there…")

- **At rest** the map is the live view: the small sun and the empty circle, the roadmaps where they are.
- **Hovering over the sun** opens the disk a little: it grows out of the sun to 0.42 of its radius, faintly, and
  closes again when the pointer leaves.
- **Clicking the sun** opens the disk fully round it, and the camera frames the disk. The sun stays at the centre.
- **Clicking the sun again** closes the disk into the sun, and the camera returns to the opening view.
- On a touch screen a tap opens or closes the disk; there is no hover. The sun answers Enter and Space from the
  keyboard. Under reduced motion the disk opens and closes without animation.

## The disk

- **Where.** It fills the empty circle, from just outside the sun's corona to just inside zone 0, the ring where the
  roadmaps begin. Nothing outside it moves when it opens.
- **Areas.** The disk is divided by the same arXiv categories as the map, in the same order round the circle, with the
  finer areas of number theory, algebraic geometry and representation theory where Mathlib has material for them.
  - Each category's share of the disk follows how much of Mathlib's key material lies in it. Outside, the shares stay
    as they are (by roadmaps), so the outer map is unchanged.
  - The disk is turned to line its categories up as well as one turn can with the same categories outside.
  - A category that has Mathlib material but no roadmaps joins the map's list of categories everywhere, as the user
    asked. At the pinned commit these are Rings and Algebras, General Topology, Dynamical Systems, Spectral Theory and
    Statistics Theory.
    - It has a sector in the disk.
    - Outside, it keeps a narrow place in the order (as a galaxy with no roadmaps would: about 0.8°), where its roadmaps
      will go. Nothing is drawn there until one arrives.
    - Those five places narrow the other sectors outside by about 5.5% and move their centres by up to 8° (median 3°).
      So the closed view is the live one with five empty slivers. Leaving them out outside is a one-line change to
      `build.py` (`also`).
- **Which items.**
  - The landmarks are the declarations that Mathlib's own catalogues name: `docs/overview.yaml`, `docs/undergrad.yaml`,
    `docs/100.yaml` and `docs/1000.yaml`. Each is titled with its catalogue's words.
  - As the camera closes in, the "Main definitions" and "Main results" that Mathlib's files list in their headers appear
    too, titled by their Lean names. The header's own description of each serves as its summary.
  - The rest of Mathlib is faint dust, as dense as Mathlib is at that area and distance.
- **Distance from the centre.**
  - Distance is the number of Mathlib definitions needed to state and prove the item: the distinct definitions,
    structures, classes and inductive types in the closure of everything its statement and its proof refer to, the
    proofs of the lemmas it uses included, recursively.
  - Lean's own foundations (core and Batteries) and the lemmas of Mathlib's tactics (`Mathlib.Tactic.…`, `Mathlib.Meta.…`,
    `Mathlib.Util.…`) do not count.
  - The scale is logarithmic, from the sun outwards.
  - An item's panel also gives the number needed to state it alone, and the longest chain of definitions beneath it.
- **Placement within a sector.** Each module has a wedge of its sector, in module order, as wide as its share of the
  sector's items. An item starts at its distance and at an angle in its module's wedge that its name gives. It then moves
  out on a spiral round that point until it is 6 units clear of the items placed before it: the landmarks first, then
  by importance.
- **Drawing.** The disk is drawn flat, with no gradients or glows; the sun and the pull requests' stars remain the only
  ones. It has a faint fill and faint rules between its areas.
  - The disk and its area names show from the opening view of the disk.
  - The items are stars, as the landed pull requests are: a near-white core in a faint halo that fades (two flat strokes),
    keeping its size on screen. A definition burns blue-white and a theorem pale gold. A landmark is brighter the more
    important it is, and a header's item is faint. None twinkles: on the atlas a twinkling star is an open pull
    request (the user, 2026-10-26: "make the blue and yellow balls into something that looks more like the stars").
  - The landmarks' names appear as the label system finds them room, the most important first.
  - Header items appear from a closer zoom.
  - Clicking an item opens its panel: its statement as Lean prints it, its docstring, the three measures above, its
    module, and links to Mathlib's docs and source.

## Data

1. **The Mathlib dataset.** `.github/workflows/mathlib-dataset.yml` runs trust-extract with `--root Mathlib` at the
   Mathlib commit Tau Ceti pins (`data/mathlib-pin.json`) and publishes it as a release. The review site's Tau Ceti
   dataset cannot serve: it has Mathlib's declarations but not their edges.
2. **`scripts/mathlib_disk.py`** (needs `evidence-core`) reads the dataset, the catalogues and the file headers of the
   same Mathlib commit, and writes `data/mathlib-disk.json`:
   - the items, with their measures, area, statement and summary;
   - the dust histogram.

   The measures are computed over the whole graph in one pass in dependency order, with HyperLogLog sketches of 1,024
   registers (about 3% error, ample for a logarithmic scale). Exact counts would need a separate closure for every item.
3. **`data/mathlib-areas.json`** places a module in an area, by the longest matching module prefix. It is a reviewed
   table; the catalogues' own subject headings are a cross-check, not the rule.
4. **The build** (stdlib Python, as now) reads `data/mathlib-disk.json`. It divides the disk among the areas, turns the
   disk to line up with the sectors outside, places the items, and embeds the result in the page.

## Files

New:
- `scripts/mathlib_disk.py`
- `scripts/disk_layout.py`
- `data/mathlib-areas.json`
- `data/mathlib-disk.json`
- the tests for each

Changed (laid over tauceti-explorer by `scripts/build.sh`):
- `scripts/build.py`, which embeds the disk;
- `scripts/arxiv_groups.py`, for the categories everywhere;
- `src/universe.js`, which places the disk;
- `src/graph.js`, which draws it and handles the sun;
- `src/app.js`, for the item panel;
- the browser checks.

## Non-goals (for now)

- Links between the disk and the roadmaps, such as which roadmap layers use a landmark.
- Search over the disk's items.
- Address-bar state for the disk.
- Refreshing the roadmaps automatically: `UPSTREAM` is moved by hand.
