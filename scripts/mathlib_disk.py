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

import re
from pathlib import Path

from evidence_core.catalogs import famous_theorems, topic_tree

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
