# Mathlib disk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An experimental Tau Ceti atlas whose Mathlib sun opens into a disk of Mathlib's key definitions and theorems,
placed by area and by how much Mathlib is needed to state and prove them.

**Architecture:** This repository is an overlay on tauceti-explorer at `UPSTREAM` (`scripts/build.sh` lays it over a
worktree in `.upstream/` and builds). A data step (`scripts/mathlib_disk.py`, run by hand, needs `requirements-data.txt`)
turns the Mathlib dataset into `data/mathlib-disk.json`. The build (standard-library Python) lays the disk out
(`scripts/disk_layout.py`) and embeds it, and the page draws it (`src/universe.js`, `src/graph.js`, `src/app.js`).

**Tech Stack:** Python 3.12 (unittest; numpy and evidence-core only in the data step), d3 v5 SVG, Playwright checks.

**Spec:** `docs/2026-10-26-mathlib-disk-design.md`

## Global Constraints

- The live atlas and the tauceti-explorer repository are never pushed to or changed; all work is in this repository.
- At rest the page is the live view: the disk is hidden (scale 0) and nothing outside it moves when it opens.
- Disk geometry, in world units: `DISK_INNER = 150` (outside the sun's corona, `CORE_RADIUS * 2.1 = 126`),
  `DISK_OUTER = 1120` (inside zone 0, `SECTOR_CORE = 1200`). Hover opens it to scale `0.34`; a click to `1`.
- Flat drawing only: no gradients or glows on the disk (the sun and the pull requests' stars keep theirs).
- The build stays standard-library Python; `numpy`/`evidence-core` are used only by `scripts/mathlib_disk.py`.
- Excluded from every measure and from the disk: modules `Mathlib.Tactic`, `Mathlib.Meta`, `Mathlib.Util`, `Mathlib.Lean`,
  `Mathlib.Testing`, `Mathlib.Deprecated`, and names matching evidence-core's `MACHINERY`.
- Item ids on the page are `mathlib:<Lean name>`; their level is `mathlib`.

## Review Focus

- A catalogue name the dataset lacks (renamed, or in Archive) is dropped and counted, never a crash or a ghost item.
- A header bullet naming notation or an unqualified name resolves only when exactly one declaration of that module
  ends with it; otherwise it is dropped.
- Hovering in and out quickly, or clicking during the hover animation, ends in a consistent state (closed or open).
- A phone tap opens the disk (no hover there), and a second tap closes it.
- A category with no roadmaps (e.g. math.GN) must not break the map, Mission status or the subject lists.

---

### Task 1: The area table

**Files:** Create `data/mathlib-areas.json`, `scripts/mathlib_areas.py`; Test `tests/test_mathlib_areas.py`

**Interfaces:**
- Produces: `load_rules(path) -> list[tuple[str, str | None]]` (prefix, area; longest prefix first; `None` = excluded);
  `area_of(module: str, rules) -> str | None` (dotted module; a prefix matches itself and `prefix.…`; unmatched → `None`).
- Areas are `math.XX` or `math.XX/<finer area id from tauceti-explorer data/arxiv-subareas.json>`.

- [ ] Write tests: `Mathlib.NumberTheory.ModularForms.Basic` → `math.NT/automorphic`; `Mathlib.NumberTheory.Pell` →
  `math.NT/other`; `Mathlib.Topology.Homotopy.Basic` → `math.AT` (longer prefix wins over `Mathlib.Topology` → `math.GN`);
  `Mathlib.Tactic.Ring` → `None`; `Mathlib.Topologyx` does not match `Mathlib.Topology`; every area in the table is a
  category of `arxiv_groups.CATEGORIES` (with a finer area that `arxiv-subareas.json` defines); every top-level Mathlib
  directory of the pinned source has a rule.
- [ ] Run, see them fail; write the module and the table; run, see them pass; commit.

### Task 2: Items from the catalogues and the file headers

**Files:** Create `scripts/mathlib_disk.py` (first part); Test `tests/test_mathlib_disk.py`

**Interfaces:**
- Produces: `catalogue_entries(docs: Path) -> dict[str, dict]` → `{name: {"title", "catalogues": [str]}}`; title priority
  100 > 1000 > overview > undergrad; a catalogue string reads `"overview: General algebra / Rings"`, `"100: 1"`.
  `header_entries(root: Path) -> dict[str, list[tuple[str, str]]]` → module → `[(written name, description)]`, from
  `## Main definitions|results|statements|theorems|declarations|constructions` sections of the module docstring.
  `resolve(written, module, names: set[str], by_module: dict[str, list[str]]) -> str | None`.
- [ ] Tests: fixtures under `tests/fixtures/mathlib/` (a two-entry overview, a 100.yaml entry with `decls: [a, b]`, a
  1000.yaml entry, a module with "## Main definitions" bullets including one notation bullet); assert titles, multi-decl
  entries, descriptions, and that `resolve("span", "M.A", …)` finds `Submodule.span` only when unique in `M.A`.
- [ ] Fail, implement, pass, commit.

### Task 3: The measures

**Files:** Modify `scripts/mathlib_disk.py`; Test `tests/test_mathlib_disk.py`

**Interfaces:**
- Produces: `Hll` helpers `registers_for(ids: np.ndarray) -> np.ndarray[uint8, 1024]`, `estimate(regs) -> float`;
  `measures(ds, g) -> Measures` with int arrays indexed by declaration id: `needed` (distinct Mathlib concepts in the
  closure along `term` edges, itself excluded), `stated` (along evidence-core's `built_from`/`about`), `depth` (longest
  chain of concepts; a concept with none below counts 1, a theorem takes its statement's deepest concept).
- [ ] Tests: `estimate` within 5% for 20,000 distinct ids and exact (±1) up to 50; on a synthetic `ltb-dataset/2` written
  by the test (decls.jsonl, meta.json, edges/*.bin as i32le pairs, empty facets) — `C ← B ← A` concepts and a theorem `T`
  whose proof uses lemma `L` about `C`, plus `Mathlib.Tactic.Foo` lemma used by `T`: `needed[T]` = 3 (A, B, C), the tactic
  lemma's concepts not counted; `depth[A]` = 3; `stated[T]` counts only its statement's concepts.
- [ ] Fail, implement (one pass in dependency order, sketches merged by `np.maximum.reduce`, back edges ignored), pass, commit.

### Task 4: The data file and the scale chart

**Files:** Modify `scripts/mathlib_disk.py` (CLI, `write_disk(...)`); Create `data/mathlib-disk.json`

**Interfaces:**
- Produces `data/mathlib-disk.json`: `{"version": 1, "mathlib", "extractor", "items": [{"name", "title", "kind",
  "module", "path", "line", "area", "tier" (1 catalogue, 2 header), "catalogues", "needed", "stated", "depth",
  "importance", "signature", "summary"}], "areas": {area: {"items", "landmarks"}}, "dust": {"bins": 40, "max",
  "areas": {area: [counts]}}, "dropped": {...}}`.
- [ ] Test: a synthetic run writes every key, tiers right, excluded modules absent, summaries ≤ 400 characters.
- [ ] Run on the real dataset; report counts and a chart of landmarks by `needed` (log) per area to the user.
- [ ] Commit.

### Task 5: Categories everywhere and the disk's layout in the build

**Files:** Modify `scripts/arxiv_groups.py`, `scripts/build.py`; Create `scripts/disk_layout.py`; Test `tests/test_disk_layout.py`, `tests/test_arxiv_groups.py`

**Interfaces:**
- `group_by_arxiv(..., also=frozenset())`: categories in `also` with no roadmaps join `atlas["groups"]` with
  `roadmapIds: []`, `distance: None`, weight 1 in `sectors()`.
- `disk_layout.layout(disk: dict, groups: list[dict]) -> dict` → `atlas["mathlibDisk"] = {"inner", "outer", "commit",
  "max", "sectors": [{"id","label","short","code","a0","a1"}], "items": [{"id","n","t","k","s","l","r","a","p","q","d",
  "i","sig","doc","m","f","ln","c"}], "dust": {...}}`, angles in degrees as `sector`.
- [ ] Tests: sector widths ∝ `items ** .85 + 1`, the map's order, `FIELD_GAP`/`AREA_GAP` between; the turn that lines up
  sector centres with the groups' (synthetic: a disk identical to the outer map gets turn 0); `radius(needed)` monotone,
  `DISK_INNER` at 0 and `DISK_OUTER` at `max`; every item inside its sector; no two items of one sector within 6 units;
  an empty-roadmap category gets a sector and `distance None` without error.
- [ ] Fail, implement, pass; build both pages with `scripts/build.sh`; commit.

### Task 6: The disk in the universe

**Files:** Modify `src/universe.js`, `src/app.js` (`universeInput` passes `disk: DATA.mathlibDisk || null`)

**Interfaces:**
- `TauUniverse.build(...)` returns `disk: {inner, outer, sectors: [{id,label,short,a0,a1 (radians)}], items: [{id,
  level:'mathlib', name, title, kind, sector, tier, x, y, importance, …}], dust: [{x,y,cls}]}`, items also in `byId`.
- [ ] Browser check (Task 9 file): `getUniverse().disk.items.length` equals the data's, each `Math.hypot(x,y)` within
  `[inner, outer]`.

### Task 7: Drawing the disk and the sun's toggle

**Files:** Modify `src/graph.js`

**Interfaces:**
- `graph.setDisk(state: 'closed'|'peek'|'open', animate=true)`, `graph.diskState`, `graph.zoomToDisk(animate)`.
- Layer `disk` between `field` and `core`; the sun gets `role=button`, `tabindex=0`, an `aria-label` that says Open/Close.
- Durations: peek 250 ms, open 450 ms, close 350 ms; none under reduced motion.
- [ ] Browser checks: rest → closed (scale 0, no `.tau-disk-item`); hover → peek (scale .34) and leave → closed; click →
  open, items shown, disk spans ≥ 70% of the shorter side; click again → closed and `atOverview()`; Enter toggles;
  rapid hover/click ends open; phone tap opens and a second closes; sector rules start at the rim while open.

### Task 8: An item's panel

**Files:** Modify `src/app.js`

- `onSelect` sends `level === 'mathlib'` to `select(id)`; `renderInspector` shows: kind ("Mathlib definition" /
  "Mathlib theorem"), title, area, the Lean name, the statement, the summary (TauMarkdown), the three measures, the
  catalogues, links to Mathlib's docs (`https://leanprover-community.github.io/mathlib4_docs/<module path>.html#<name>`)
  and source (`https://github.com/leanprover-community/mathlib4/blob/<commit>/<path>#L<line>`).
- [ ] Browser check: clicking a landmark opens this panel with each part present and both links well formed.

### Task 9: Checks, build and publication

**Files:** Create `tests/validate_disk_browser.py`; run `tests/validate_browser.py`, `tests/validate_tauceti_browser.py`

- [ ] All unit tests (`python3 -m unittest discover -s tests` in `.upstream/` after `scripts/build.sh`) and the three
  browser suites pass; no page errors.
- [ ] Commit the built `index.html`, `tauceti/index.html`; enable Pages (main, root); open the live URL and check it.
