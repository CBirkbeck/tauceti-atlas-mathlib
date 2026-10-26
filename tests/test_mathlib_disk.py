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


if __name__ == "__main__":
    unittest.main()
