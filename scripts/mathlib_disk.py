#!/usr/bin/env python3
"""Mathlib's key definitions and theorems for the disk, from the Mathlib dataset (the release the workflow
mathlib-dataset.yml publishes), Mathlib's catalogues and its files' headers at the same commit.

  .venv/bin/python scripts/mathlib_disk.py --dataset DIR --source MATHLIB_DIR [--out data/mathlib-disk.json]

The landmarks are the declarations Mathlib's catalogues name (docs/overview.yaml, docs/undergrad.yaml, docs/100.yaml,
docs/1000.yaml), titled in the catalogues' words; the rest of the items are the main definitions and results its files
list in their headers ("## Main definitions", "## Main results", …). Each is placed by its module's area
(data/mathlib-areas.json) and measured by how much of Mathlib it needs (measures()). Needs requirements-data.txt;
the page's build does not.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from evidence_core.catalogs import famous_theorems, topic_tree
from evidence_core.graphs import is_machinery

from mathlib_areas import area_of

# The catalogues, in the order their titles are preferred: the famous theorems' own titles before a subject tree's.
LISTS = (("100", "100.yaml"), ("1000", "1000.yaml"))
TREES = (("overview", "overview.yaml"), ("undergrad", "undergrad.yaml"))
MAIN_HEADING = re.compile(r"^##\s+(?:main|key)\b[^\n]*?(?:definition|result|statement|theorem|declaration|construction)", re.I | re.M)
SECTION_HEADING = re.compile(r"^##\s", re.M)
BULLET = re.compile(r"^\s{0,3}[*-]\s+(.*)$")
LEADING_NAME = re.compile(r"\s*`([^`]+)`\s*(?:,\s*(?:and\s+|or\s+)?|and\s+|or\s+)?")
NAME = re.compile(r"[^\s`,:()\[\]{}]+")


def _title(text: str) -> str:
    """A subject tree's leaves are lower case ("complete metric space"): the first letter goes up."""
    return text[:1].upper() + text[1:] if text[:1].islower() else text


def catalogue_entries(docs: Path) -> dict[str, dict]:
    """Each declaration a catalogue names: {"title", "catalogues": [[catalogue, where]]}, where is a subject tree's
    "Area / Subarea" or a famous theorem's title. The title is the first famous list's that names it, else the first
    subject tree's."""
    found: dict[str, dict] = {}

    def add(name: str, title: str, where: list[str], rank: int) -> None:
        entry = found.setdefault(name, {"title": title, "catalogues": [], "rank": rank})
        entry["catalogues"].append(where)
        if rank < entry["rank"]:
            entry["title"], entry["rank"] = title, rank

    for rank, (key, file) in enumerate(LISTS):
        if (docs / file).exists():
            for entry in famous_theorems(docs / file):
                for name in entry.decls:
                    add(name, entry.title, [key, entry.title], rank)

    def walk(topic, path: list[str], key: str, rank: int) -> None:
        for entry in topic.entries:
            for name in entry.decls:
                add(name, _title(entry.title), [key, " / ".join(path)], rank)
        for child in topic.children:
            walk(child, path + [child.title], key, rank)

    for rank, (key, file) in enumerate(TREES, start=len(LISTS)):
        if (docs / file).exists():
            walk(topic_tree(docs / file), [], key, rank)
    for entry in found.values():
        del entry["rank"]
    return found


def module_name(root: Path, path: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def _bullets(section: str) -> list[str]:
    """The text of each bullet of a section, its indented continuation lines joined to it."""
    out: list[str] = []
    for line in section.splitlines():
        m = BULLET.match(line)
        if m and not line.startswith("    "):
            out.append(m.group(1).strip())
        elif out and line.strip() and line[:1].isspace():
            out[-1] += " " + line.strip()
        elif not line.strip() and out:
            out.append("")
    return [text for text in out if text]


def header_names(docstring: str) -> list[tuple[str, str]]:
    """(name, the bullet's words) for each name a Main section's bullets start with."""
    out: list[tuple[str, str]] = []
    for heading in MAIN_HEADING.finditer(docstring):
        following = SECTION_HEADING.search(docstring, heading.end())
        for text in _bullets(docstring[heading.end():following.start() if following else len(docstring)]):
            names, at = [], 0
            while m := LEADING_NAME.match(text, at):
                names.append(m.group(1).strip())
                at = m.end()
            words = re.sub(r"^\s*[:—–-]\s*", "", text[at:]).strip()
            out += [(name, words) for name in names if NAME.fullmatch(name)]
    return out


def header_entries(root: Path) -> dict[str, list[tuple[str, str]]]:
    """For each module under root/Mathlib, the names its header's Main sections list, with their words."""
    found: dict[str, list[tuple[str, str]]] = {}
    for path in sorted((root / "Mathlib").rglob("*.lean")):
        text = path.read_text(encoding="utf-8", errors="replace")
        start = text.find("/-!")
        if start < 0:
            continue
        end = text.find("-/", start)
        names = header_names(text[start + 3:end if end > 0 else len(text)])
        if names:
            found[module_name(root, path)] = names
    return found


def resolve(written: str, module: str, names: set[str], by_module: dict[str, list[str]]) -> str | None:
    """The declaration a header means by a name: the name itself, else the one declaration of its module whose
    name ends with it (a header writes `span` for `Submodule.span`), else none."""
    if written in names:
        return written
    ending = [name for name in by_module.get(module, ()) if name.endswith("." + written)]
    return ending[0] if len(ending) == 1 else None


# --- how much of Mathlib a declaration needs --------------------------------------------------------------------
# A closure is counted exactly while it is small, and by a HyperLogLog sketch of REGISTERS registers once it is not
# (about 3% error, ample for the disk's logarithmic scale): each declaration's closure is the union of its
# dependencies' closures, so the sketches merge register by register, in one pass in dependency order.
P_BITS = 10
REGISTERS = 1 << P_BITS
EXACT = 128
ALPHA = .7213 / (1 + 1.079 / REGISTERS)
_M64 = np.uint64(0xFFFFFFFFFFFFFFFF)


def _hashes(ids: np.ndarray) -> np.ndarray:
    """splitmix64 of each id: well-spread 64-bit hashes."""
    with np.errstate(over="ignore"):
        z = np.asarray(ids, dtype=np.int64).astype(np.uint64) + np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return (z ^ (z >> np.uint64(31))) & _M64


def _bit_length(w: np.ndarray) -> np.ndarray:
    n = np.zeros(w.shape, dtype=np.int64)
    for s in (32, 16, 8, 4, 2, 1):
        high = w >= (np.uint64(1) << np.uint64(s))
        n[high] += s
        w = np.where(high, w >> np.uint64(s), w)
    return n + (w > 0)


def _slots(ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Each id's register and rank (the leading zeros of the rest of its hash, plus one)."""
    h = _hashes(ids)
    rest = 64 - P_BITS
    return (h >> np.uint64(rest)).astype(np.int64), (rest - _bit_length(h & np.uint64((1 << rest) - 1)) + 1).astype(np.uint8)


def registers_for(ids: np.ndarray) -> np.ndarray:
    """The sketch of a set of declaration ids."""
    regs = np.zeros(REGISTERS, dtype=np.uint8)
    if len(ids):
        index, rank = _slots(np.asarray(ids))
        np.maximum.at(regs, index, rank)
    return regs


def estimate(regs: np.ndarray) -> float:
    """How many distinct ids a sketch holds (linear counting while many registers are empty)."""
    zeros = int(np.count_nonzero(regs == 0))
    raw = ALPHA * REGISTERS * REGISTERS / float(np.sum(np.ldexp(1.0, -regs.astype(np.int64))))
    return REGISTERS * math.log(REGISTERS / zeros) if raw <= 2.5 * REGISTERS and zeros else raw


def _postorder(nodes, children) -> list[int]:
    """The nodes, each after everything beneath it; an edge back to a node still being visited is not followed."""
    state: dict[int, int] = {}
    order: list[int] = []
    for root in nodes:
        if root in state:
            continue
        state[root] = 1
        stack = [(root, iter(children(root)))]
        while stack:
            x, it = stack[-1]
            for c in it:
                if c not in state:
                    state[c] = 1
                    stack.append((c, iter(children(c))))
                    break
            else:
                stack.pop()
                state[x] = 2
                order.append(x)
    return order


def _counts(order: list[int], children, counted) -> dict[int, int]:
    """For each node, in an order with everything beneath a node before it: how many counted nodes lie beneath it,
    itself excluded. A closure (itself included when counted) is a set while it has at most EXACT members, else a
    sketch."""
    small: dict[int, frozenset] = {}
    big: dict[int, np.ndarray] = {}
    count: dict[int, int] = {}
    for x in order:
        kids = [c for c in children(x) if c in small or c in big]
        exact = [small[c] for c in kids if c in small]
        if len(exact) == len(kids):
            ids = frozenset().union(*exact)
            count[x] = len(ids)
            if len(ids) <= EXACT:
                small[x] = ids | {x} if counted(x) else ids
                continue
            regs = registers_for(np.fromiter(ids, dtype=np.int64, count=len(ids)))
        else:
            sketches = [big[c] for c in kids if c in big]
            regs = np.max(np.stack(sketches), axis=0) if len(sketches) > 1 else sketches[0].copy()
            if exact:
                ids = frozenset().union(*exact)
                np.maximum(regs, registers_for(np.fromiter(ids, dtype=np.int64, count=len(ids))), out=regs)
            count[x] = round(estimate(regs))
        if counted(x):
            index, rank = _slots(np.array([x]))
            regs[index[0]] = max(regs[index[0]], rank[0])
        big[x] = regs
    return count


@dataclass
class Measures:
    """Per declaration id: the Mathlib definitions needed to state and prove it (`needed`), to state it (`stated`),
    and the longest chain of definitions beneath it, itself included when it is one (`depth`). A definition is a
    concept of evidence-core's graphs: a definition, structure, class or inductive type, not a proof or instance."""
    needed: np.ndarray
    stated: np.ndarray
    depth: np.ndarray
    excluded: np.ndarray


def measures(ds, g, rules) -> Measures:
    """The measures of every declaration of the library (the dataset's project, Mathlib). Lean's own declarations,
    and the tactics' (evidence-core's machinery, and the modules the area table leaves out), are neither counted nor
    gone through."""
    rules = sorted(rules, key=lambda rule: -len(rule[0].split(".")))
    n = len(ds.decls)
    excluded = np.array([not d.is_project or is_machinery(d.name) or area_of(d.module, rules) is None for d in ds.decls])
    concept = np.frombuffer(bytes(g.concept), dtype=np.uint8).astype(bool) & ~excluded
    nodes = [d.id for d in ds.decls if not excluded[d.id]]
    term = ds.edges("term")
    below_cache: dict[int, tuple[int, ...]] = {}

    def below(x: int) -> tuple[int, ...]:
        """The concepts a declaration's statement is about, or a concept is built from."""
        if x not in below_cache:
            found = g.built_from(x) if g.concept[x] else g.about(x)
            below_cache[x] = tuple(c for c in found if c != x and concept[c])
        return below_cache[x]

    def uses(x: int) -> list[int]:
        return [t for t in term.get(x, ()) if t != x and not excluded[t]]

    needed = _counts(_postorder(nodes, uses), uses, lambda x: bool(concept[x]))
    order = _postorder(nodes, below)
    stated = _counts(order, below, lambda x: bool(concept[x]))
    depth = np.zeros(n, dtype=np.int32)
    for x in order:
        depth[x] = (1 if concept[x] else 0) + max((int(depth[c]) for c in below(x)), default=0)
    as_array = lambda values: np.array([values.get(i, 0) for i in range(n)], dtype=np.int32)
    return Measures(needed=as_array(needed), stated=as_array(stated), depth=depth, excluded=excluded)
