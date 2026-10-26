"""The data step of the Mathlib disk (scripts/mathlib_disk.py). It needs evidence-core, numpy and PyYAML
(requirements-data.txt): run it with the data environment, `.venv/bin/python -m unittest tests.test_mathlib_disk`.
Without them these tests are skipped, so the page's own suite runs with the standard library alone."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import evidence_core  # noqa: F401
    import numpy  # noqa: F401
    import yaml  # noqa: F401
except ImportError:
    md = None
else:
    import mathlib_disk as md  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "mathlib"


@unittest.skipUnless(md, "needs requirements-data.txt")
class Catalogues(unittest.TestCase):
    """The landmarks: the declarations Mathlib's catalogues name, with the catalogues' words for them."""

    def setUp(self):
        self.found = md.catalogue_entries(FIXTURES / "docs")

    def test_a_subject_tree_names_its_declarations_with_their_place_in_the_tree(self):
        self.assertEqual(self.found["CompleteSpace"]["catalogues"], [["overview", "Topology / Metric spaces"]])
        self.assertEqual(self.found["CompleteSpace"]["title"], "Complete metric space")

    def test_a_declaration_named_twice_keeps_every_catalogue(self):
        self.assertEqual(self.found["IsDedekindDomain"]["catalogues"],
                         [["overview", "General algebra / Rings"], ["undergrad", "Ring Theory / Ideals"]])

    def test_the_famous_lists_title_it_first_freeks_hundred_before_the_thousand(self):
        entry = self.found["irrational_sqrt_two"]
        self.assertEqual(entry["title"], "The Irrationality of the Square Root of 2")
        self.assertEqual([c[0] for c in entry["catalogues"]], ["100", "1000"])

    def test_every_declaration_of_an_entry_is_a_landmark_and_one_without_any_is_none(self):
        self.assertEqual(self.found["num_dvd_of_is_root"]["title"], "Rational root theorem")
        self.assertIn("den_dvd_of_is_root", self.found)
        self.assertNotIn("", self.found)
        self.assertFalse(any("Prime Number Theorem" == e["title"] for e in self.found.values()))


@unittest.skipUnless(md, "needs requirements-data.txt")
class Headers(unittest.TestCase):
    """The main definitions and results a file's header lists, with its words for each."""

    def setUp(self):
        self.found = md.header_entries(FIXTURES)

    def test_each_name_a_main_section_lists_with_the_bullets_words(self):
        listed = dict(self.found["Mathlib.RingTheory.Example"])
        self.assertEqual(listed["IsDedekindDomain"], "defines a Dedekind domain as a Dedekind ring that is a domain.")
        self.assertEqual(listed["span"], "the submodule spanned by a set.")

    def test_a_bullet_naming_several_gives_each_the_same_words_across_subheadings(self):
        listed = dict(self.found["Mathlib.RingTheory.Example"])
        for name in ("Ideal.isMaximal_iff", "Ideal.IsMaximal.ne_top", "Ideal.exists_le_maximal"):
            self.assertEqual(listed[name], "maximal ideals, characterised.")

    def test_notation_and_other_sections_are_not_names(self):
        names = [name for name, _ in self.found["Mathlib.RingTheory.Example"]]
        self.assertNotIn("notThisOne", names)
        self.assertFalse(any(" " in name for name in names))

    def test_resolving_a_written_name(self):
        names = {"IsDedekindDomain", "Submodule.span", "Set.span", "Ideal.span"}
        by_module = {"M.A": ["Submodule.span", "IsDedekindDomain"], "M.B": ["Set.span", "Ideal.span"]}
        self.assertEqual(md.resolve("IsDedekindDomain", "M.B", names, by_module), "IsDedekindDomain")
        self.assertEqual(md.resolve("span", "M.A", names, by_module), "Submodule.span")
        self.assertIsNone(md.resolve("span", "M.B", names, by_module))  # two in M.B end with it
        self.assertIsNone(md.resolve("span", "M.C", names, by_module))


def write_dataset(root: Path, decls: list[tuple], edges: dict[str, list[tuple[int, int]]]) -> Path:
    """A dataset in the extractor's format (ltb-dataset/2): decls are (name, module, kind, isProp, package)."""
    import json
    from array import array
    (root / "edges").mkdir(parents=True)
    with (root / "decls.jsonl").open("w", encoding="utf-8") as f:
        for i, (name, module, kind, is_prop, package) in enumerate(decls):
            f.write(json.dumps({"id": i, "name": name, "module": module, "kind": kind, "isProp": is_prop, "package": package,
                                "scope": "project" if package == "mathlib" else "upstream", "hashes": {}}) + "\n")
    entries = []
    for notion, pairs in edges.items():
        data = array("i", [x for pair in pairs for x in pair])
        (root / "edges" / f"{notion}.bin").write_bytes(data.tobytes())
        entries.append({"name": notion, "format": "i32le-pairs", "file": f"edges/{notion}.bin", "count": len(pairs)})
    (root / "meta.json").write_text(json.dumps({"spec": "ltb-dataset/2", "edges": entries, "facets": [],
                                                "library": {"commit": "c0ffee"}}), encoding="utf-8")
    return root


@unittest.skipUnless(md, "needs requirements-data.txt")
class Sketches(unittest.TestCase):
    """Counting distinct definitions without holding every closure: HyperLogLog, exact while small."""

    def test_a_large_count_is_within_five_percent(self):
        import numpy as np
        for n in (2_000, 20_000, 200_000):
            estimate = md.estimate(md.registers_for(np.arange(n, dtype=np.int64)))
            self.assertLess(abs(estimate - n) / n, .05, n)

    def test_merging_is_the_union(self):
        import numpy as np
        a, b = md.registers_for(np.arange(0, 6000, dtype=np.int64)), md.registers_for(np.arange(4000, 10_000, dtype=np.int64))
        self.assertLess(abs(md.estimate(np.maximum(a, b)) - 10_000) / 10_000, .05)

    def test_an_empty_sketch_counts_nothing(self):
        import numpy as np
        self.assertEqual(round(md.estimate(md.registers_for(np.arange(0, dtype=np.int64)))), 0)


@unittest.skipUnless(md, "needs requirements-data.txt")
class Measures(unittest.TestCase):
    """How much of Mathlib a declaration needs: to state it, to state and prove it, and its deepest chain."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        from evidence_core.dataset import Dataset
        from evidence_core.graphs import Graphs
        decls = [("A", "Mathlib.Foo.A", "definition", False, "mathlib"),              # 0, built on Nat only
                 ("B", "Mathlib.Foo.B", "definition", False, "mathlib"),              # 1, built on A
                 ("C", "Mathlib.Foo.C", "structure", False, "mathlib"),               # 2, built on B
                 ("L", "Mathlib.Foo.L", "theorem", True, "mathlib"),                  # 3, about C
                 ("T", "Mathlib.Foo.T", "theorem", True, "mathlib"),                  # 4, about A; its proof uses L and K
                 ("Mathlib.Tactic.Ring.K", "Mathlib.Tactic.Ring.Basic", "theorem", True, "mathlib"),  # 5, about D
                 ("D", "Mathlib.Foo.D", "definition", False, "mathlib"),              # 6, only the tactic lemma uses it
                 ("Nat", "Init.Prelude", "inductive", False, "lean4"),                # 7, Lean's own
                 ("E", "Mathlib.Foo.E", "definition", False, "mathlib")]              # 8, built on B and C
        meaning = [(0, 7), (1, 0), (2, 1), (3, 2), (4, 0), (5, 6), (8, 1), (8, 2)]
        term = meaning + [(4, 3), (4, 5)]
        root = write_dataset(Path(tempfile.mkdtemp()) / "ds", decls, {"meaning": meaning, "statement": meaning, "term": term})
        ds = Dataset.load(root)
        rules = [("Mathlib.Tactic", None), ("Mathlib", "math.LO")]
        cls.m = md.measures(ds, Graphs(ds), rules)
        cls.id = {d.name: d.id for d in ds.decls}

    def at(self, measure, name):
        return int(getattr(self.m, measure)[self.id[name]])

    def test_to_state_and_prove_counts_every_definition_beneath_its_statement_and_its_proofs_lemmas(self):
        self.assertEqual(self.at("needed", "T"), 3)   # A from its statement; C, B from the lemma L its proof uses
        self.assertEqual(self.at("needed", "L"), 3)
        self.assertEqual(self.at("needed", "A"), 0)   # Lean's Nat does not count

    def test_a_tactics_lemmas_and_what_only_they_use_do_not_count(self):
        self.assertEqual(self.at("needed", "T"), 3)   # not D, which only the tactic lemma K mentions

    def test_to_state_counts_only_the_statements_definitions(self):
        self.assertEqual(self.at("stated", "T"), 1)
        self.assertEqual(self.at("stated", "C"), 2)
        self.assertEqual(self.at("stated", "E"), 3)   # B and C, and A beneath both, once

    def test_the_deepest_chain_of_definitions(self):
        self.assertEqual(self.at("depth", "A"), 1)
        self.assertEqual(self.at("depth", "C"), 3)
        self.assertEqual(self.at("depth", "E"), 4)
        self.assertEqual(self.at("depth", "L"), 3)    # a theorem takes its statement's deepest definition
        self.assertEqual(self.at("depth", "T"), 1)


if __name__ == "__main__":
    unittest.main()
