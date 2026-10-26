"""The Mathlib disk on the published pages: where its sectors and items lie (data/mathlib-disk.json, from
scripts/mathlib_disk.py).

The disk fills the empty circle round the sun, from DISK_INNER (outside the corona) to DISK_OUTER (inside zone 0, where
the roadmaps begin). It is divided as the map is, by arXiv category and finer area, in the map's order round the circle;
each sector's share grows with its items (as a galaxy's grows with its roadmaps, scripts/arxiv_groups.py), and the
whole division is turned to line up with the map's sectors as well as one turn can. An item lies as far out as the
Mathlib definitions it needs (on a logarithmic scale up to the deepest declaration of Mathlib), in its module's wedge
of the sector, moved a little round that point until it is clear of the items already placed; the landmarks are placed
first.
"""
from __future__ import annotations

import math
import zlib
from collections import Counter, defaultdict

from arxiv_groups import AREA_GAP, FIELD_GAP

DISK_INNER, DISK_OUTER = 150, 1120
# The least distance between two items of one sector, in the map's units.
SPACING = 6
# The turn is chosen on a grid of this many degrees.
TURN_STEP = .1
# The spiral an item moves out along to find room: how many points it tries, and the golden angle between them.
SPIRAL = 1200
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))


def area_sector(area: str | None, ids: set[str]) -> str | None:
    """The disk's sector for an item's area: the area when the map has it; else, for a finer area, its category's
    catch-all area or the category itself; else None."""
    if not area:
        return None
    if area in ids:
        return area
    code = area.split("/")[0]
    return next((sid for sid in (f"{code}/other", code) if sid in ids), None)


def _wrap(degrees: float) -> float:
    return (degrees + 180) % 360 - 180


def disk_sectors(counts: dict[str, int], groups: list[dict]) -> list[dict]:
    """The disk's sectors: one for each of the map's sectors (groups) with items, in the map's order, a share that
    grows with its items, gaps as on the map; turned so that each lies as near its sector on the map as one turn of
    the whole allows (the misfit of each weighted by its share). Angles in degrees, clockwise from the right."""
    ordered = [g for g in sorted(groups, key=lambda g: g["sector"][0]) if counts.get(g["id"], 0) > 0]
    if not ordered:
        return []
    weight = {g["id"]: counts[g["id"]] ** .85 + 1 for g in ordered}
    gaps = [0.0] + [AREA_GAP if b.get("field") and b.get("field") == a.get("field") else FIELD_GAP for a, b in zip(ordered, ordered[1:])]
    unit = (360 - sum(gaps) - FIELD_GAP) / sum(weight.values())
    spans, angle = [], 0.0
    for gap, g in zip(gaps, ordered):
        angle += gap
        spans.append((angle, angle + weight[g["id"]] * unit))
        angle += weight[g["id"]] * unit
    centres = [((g["sector"][0] + g["sector"][1]) / 2, (a0 + a1) / 2, weight[g["id"]]) for g, (a0, a1) in zip(ordered, spans)]

    def misfit(turn: float) -> float:
        return sum(w * _wrap(turn + mine - theirs) ** 2 for theirs, mine, w in centres)

    turn = min((k * TURN_STEP for k in range(int(360 / TURN_STEP))), key=lambda t: (round(misfit(t), 9), t))
    return [{"id": g["id"], "label": g.get("label") or g["id"], "short": g.get("short") or g.get("label") or g["id"],
             "code": g["id"].split("/")[0], "field": g.get("field"), "color": g.get("color"),
             "a0": round(a0 + turn, 3), "a1": round(a1 + turn, 3), "items": counts[g["id"]]} for g, (a0, a1) in zip(ordered, spans)]


def radius(needed: int, top: int) -> float:
    """How far out an item lies: logarithmic in the definitions it needs, from DISK_INNER (none) to DISK_OUTER (the
    deepest declaration of Mathlib)."""
    if top <= 0:
        return float(DISK_INNER)
    return DISK_INNER + (DISK_OUTER - DISK_INNER) * math.log1p(max(0, min(needed, top))) / math.log1p(top)


def _unit(text: str) -> float:
    """A number in [0, 1) that a name always gives."""
    return zlib.crc32(text.encode("utf-8")) / 2 ** 32


def place_items(items: list[dict], sectors: list[dict], top: int) -> None:
    """Give each item its radius `r` and angle `a` (degrees) in its sector (item["sector"]). Each module has a wedge of
    its sector, in module order, as wide as its share of the sector's items; an item starts at its distance, at an
    angle in its module's wedge that its name gives, and moves out along a spiral round that point, staying in its
    sector, until it is SPACING clear of the items already placed (the landmarks first, then by importance)."""
    by_sector = defaultdict(list)
    for item in items:
        by_sector[item["sector"]].append(item)
    for sector in sectors:
        members = by_sector.get(sector["id"], [])
        if not members:
            continue
        a0, a1 = math.radians(sector["a0"]), math.radians(sector["a1"])
        sizes = Counter(item["module"] for item in members)
        wedge, at = {}, a0
        for module in sorted(sizes):
            span = (a1 - a0) * sizes[module] / len(members)
            wedge[module], at = (at, at + span), at + span
        grid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)

        def crowd(x: float, y: float) -> float:
            cx, cy = int(x // SPACING), int(y // SPACING)
            return max((SPACING - math.hypot(u - x, v - y) for i in (-1, 0, 1) for j in (-1, 0, 1)
                        for (u, v) in grid.get((cx + i, cy + j), ())), default=0.0)

        for item in sorted(members, key=lambda i: (i["tier"], -i["importance"], i["name"])):
            w0, w1 = wedge[item["module"]]
            start, distance = w0 + (w1 - w0) * _unit(item["name"]), radius(item["needed"], top)
            x0, y0 = distance * math.cos(start), distance * math.sin(start)
            best = None
            for k in range(SPIRAL):
                step = SPACING * .62 * math.sqrt(k)
                x, y = x0 + step * math.cos(k * GOLDEN_ANGLE), y0 + step * math.sin(k * GOLDEN_ANGLE)
                r = math.hypot(x, y)
                if r < DISK_INNER - SPACING * 6 or r > DISK_OUTER + SPACING * 6:
                    continue
                angle = a0 + (math.atan2(y, x) - a0) % (2 * math.pi)
                margin = min((a1 - a0) / 2, SPACING / 2 / r)
                if angle < a0 + margin or angle > a1 - margin:
                    continue
                c = crowd(x, y)
                if best is None or c < best[0] - 1e-9:
                    best = (c, x, y, r, angle)
                if c <= 1e-9:
                    break
            if best is None:
                best = (0.0, x0, y0, distance, start)
            _, x, y, r, angle = best
            grid[(int(x // SPACING), int(y // SPACING))].append((x, y))
            item["r"], item["a"] = round(r, 2), round(math.degrees(angle), 3)


def layout(disk: dict, groups: list[dict]) -> dict:
    """The page's disk: its sectors, its items placed, and the dust by sector."""
    ids = {g["id"] for g in groups}
    items = [{**item, "sector": area_sector(item["area"], ids)} for item in disk["items"]]
    items = [item for item in items if item["sector"]]
    counts = Counter(item["sector"] for item in items)
    sectors = disk_sectors(counts, groups)
    top = disk["dust"]["max"]
    place_items(items, sectors, top)
    bins = disk["dust"]["bins"]
    dust: dict[str, list[int]] = {}
    for area, values in disk["dust"]["areas"].items():
        sid = area_sector(area, ids)
        if sid in counts:
            merged = dust.setdefault(sid, [0] * bins)
            for k, value in enumerate(values):
                merged[k] += value
    return {"inner": DISK_INNER, "outer": DISK_OUTER, "commit": disk["mathlib"], "max": top, "measure": disk.get("measure", ""),
            "sectors": sectors,
            "items": [{"id": "mathlib:" + item["name"], "n": item["name"], "t": item["title"], "k": item.get("keyword") or item["kind"],
                       "s": item["sector"], "l": item["tier"], "r": item["r"], "a": item["a"], "p": item["needed"], "q": item["stated"],
                       "d": item["depth"], "i": item["importance"], "sig": item["signature"], "doc": item["summary"], "m": item["module"],
                       "f": item["path"], "ln": item["line"], "c": item["catalogues"]} for item in items],
            "dust": {"bins": bins, "areas": dust}}
