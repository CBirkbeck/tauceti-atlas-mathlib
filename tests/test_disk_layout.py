import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from arxiv_groups import AREA_GAP, FIELD_GAP, sectors  # noqa: E402
from disk_layout import DISK_INNER, DISK_OUTER, SPACING, area_sector, disk_sectors, layout, place_items, radius  # noqa: E402


def group(gid, a0, a1, field=None, label=None):
    return {"id": gid, "sector": [a0, a1], "field": field, "label": label or gid, "short": label or gid, "roadmapIds": []}


# Outer sectors as the map has them: number theory divided into areas, then algebraic geometry, an empty general
# topology and combinatorics.
GROUPS = [group("math.NT/analytic", 40, 90, "math.NT"), group("math.NT/other", 90.8, 130, "math.NT"), group("math.AG", 132.5, 190),
          group("math.GN", 192.5, 193.5), group("math.CO", 196, 220)]


class AreaSectors(unittest.TestCase):
    """The sector of the disk an item's area falls in: its own when the map has it, else its category's."""

    def test_an_area_the_map_has_is_its_own_sector(self):
        ids = {g["id"] for g in GROUPS}
        self.assertEqual(area_sector("math.NT/analytic", ids), "math.NT/analytic")
        self.assertEqual(area_sector("math.GN", ids), "math.GN")

    def test_a_finer_area_the_map_lacks_goes_to_its_categorys_catch_all_else_the_category(self):
        self.assertEqual(area_sector("math.NT/iwasawa", {g["id"] for g in GROUPS}), "math.NT/other")
        self.assertEqual(area_sector("math.RT/lie", {"math.RT"}), "math.RT")
        self.assertIsNone(area_sector("math.RT/lie", {"math.NT/other"}))


class Sectors(unittest.TestCase):
    """The disk's division: the map's order, a share that grows with the items, and turned to line up with the map."""

    def setUp(self):
        self.disk = disk_sectors({"math.NT/analytic": 100, "math.NT/other": 310, "math.GN": 500, "math.CO": 50}, GROUPS)
        self.by_id = {s["id"]: s for s in self.disk}

    def test_one_sector_for_each_area_with_items_in_the_maps_order(self):
        self.assertEqual([s["id"] for s in self.disk], ["math.NT/analytic", "math.NT/other", "math.GN", "math.CO"])

    def test_a_share_grows_with_the_items(self):
        width = {s["id"]: s["a1"] - s["a0"] for s in self.disk}
        self.assertAlmostEqual(width["math.GN"] / width["math.CO"], (500 ** .85 + 1) / (50 ** .85 + 1), places=2)

    def test_gaps_as_on_the_map_and_the_whole_circle(self):
        a, b = self.by_id["math.NT/analytic"], self.by_id["math.NT/other"]
        self.assertAlmostEqual(b["a0"] - a["a1"], AREA_GAP, places=2)
        self.assertAlmostEqual(self.by_id["math.GN"]["a0"] - b["a1"], FIELD_GAP, places=2)
        widths = sum(s["a1"] - s["a0"] for s in self.disk)
        self.assertAlmostEqual(widths + AREA_GAP + 3 * FIELD_GAP, 360, places=1)  # and the gap that closes the circle

    def test_a_disk_shared_out_as_the_map_is_turned_onto_it(self):
        outer = [{"id": gid, "roadmapIds": ["r"] * n, "field": field} for gid, n, field in
                 (("math.NT/analytic", 30, "math.NT"), ("math.NT/other", 12, "math.NT"), ("math.GN", 1, None), ("math.CO", 7, None))]
        sectors(outer)
        disk = disk_sectors({g["id"]: len(g["roadmapIds"]) for g in outer}, outer)
        for mine, theirs in zip(disk, outer):
            self.assertAlmostEqual(mine["a0"], theirs["sector"][0], delta=.1)
            self.assertAlmostEqual(mine["a1"], theirs["sector"][1], delta=.1)


class Placement(unittest.TestCase):
    """Where an item lies: as far out as the Mathlib it needs, in its sector, clear of the others."""

    def test_the_radius_runs_from_the_inner_edge_to_the_rim_and_grows_with_what_is_needed(self):
        self.assertEqual(radius(0, 50_000), DISK_INNER)
        self.assertAlmostEqual(radius(50_000, 50_000), DISK_OUTER)
        values = [radius(n, 50_000) for n in (0, 1, 10, 100, 1000, 10_000, 50_000)]
        self.assertEqual(values, sorted(values))

    def test_items_stay_in_their_sector_and_apart(self):
        rng = random.Random(7)
        disk = disk_sectors({"math.GN": 400, "math.CO": 120}, GROUPS)
        items = [{"name": f"n{i}", "module": f"Mathlib.M{i % 17}", "sector": "math.GN" if i < 400 else "math.CO", "tier": 1 + (i % 3 == 0),
                  "importance": rng.random(), "needed": int(math.exp(rng.uniform(0, math.log(40_000))))} for i in range(520)]
        place_items(items, disk, 40_000)
        bounds = {s["id"]: (s["a0"], s["a1"]) for s in disk}
        for item in items:
            a0, a1 = bounds[item["sector"]]
            self.assertTrue(a0 <= item["a"] <= a1, item)
            self.assertTrue(DISK_INNER - SPACING * 6 <= item["r"] <= DISK_OUTER + SPACING * 6, item)
        where = [(i["sector"], i["r"] * math.cos(math.radians(i["a"])), i["r"] * math.sin(math.radians(i["a"]))) for i in items]
        close = sum(1 for k, (s, x, y) in enumerate(where) for (t, u, v) in where[k + 1:] if s == t and math.hypot(x - u, y - v) < SPACING - 1e-6)
        self.assertEqual(close, 0)


class Layout(unittest.TestCase):
    """What the page is given: the disk's sectors, its items with their places, and the dust by sector."""

    def test_the_pages_disk(self):
        disk = {"mathlib": "c0ffee", "measure": "…", "items": [
            {"name": "Nat.Prime", "title": "Prime number", "kind": "definition", "keyword": "def", "module": "Mathlib.Data.Nat.Prime.Defs",
             "path": "Mathlib/Data/Nat/Prime/Defs.lean", "line": 40, "area": "math.NT/other", "tier": 1, "catalogues": [["overview", "Number theory / Primes"]],
             "needed": 20, "stated": 8, "depth": 4, "importance": 9.1, "signature": "Nat.Prime (p : ℕ) : Prop", "summary": "A prime."},
            {"name": "CompactSpace", "title": "Compact space", "kind": "class", "keyword": "class", "module": "Mathlib.Topology.Defs", "path": "Mathlib/Topology/Defs.lean",
             "line": 9, "area": "math.GN", "tier": 2, "catalogues": [], "needed": 300, "stated": 50, "depth": 9, "importance": 5.0,
             "signature": "CompactSpace (X : Type u) [TopologicalSpace X] : Prop", "summary": ""}],
            "areas": {"math.NT/other": {"items": 1, "landmarks": 1}, "math.GN": {"items": 1, "landmarks": 0}},
            "dust": {"bins": 3, "max": 1000, "areas": {"math.NT/other": [1, 2, 3], "math.NT/iwasawa": [1, 0, 0], "math.GN": [0, 5, 0]}}}
        page = layout(disk, GROUPS)
        self.assertEqual((page["inner"], page["outer"], page["commit"], page["max"]), (DISK_INNER, DISK_OUTER, "c0ffee", 1000))
        self.assertEqual([s["id"] for s in page["sectors"]], ["math.NT/other", "math.GN"])
        prime = next(i for i in page["items"] if i["n"] == "Nat.Prime")
        self.assertEqual((prime["id"], prime["t"], prime["s"], prime["l"], prime["p"], prime["q"], prime["d"]),
                         ("mathlib:Nat.Prime", "Prime number", "math.NT/other", 1, 20, 8, 4))
        self.assertEqual(page["dust"]["areas"], {"math.NT/other": [2, 2, 3], "math.GN": [0, 5, 0]})


if __name__ == "__main__":
    unittest.main()
