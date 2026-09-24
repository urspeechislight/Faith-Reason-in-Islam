"""Content-boundary regressions using unpublished fixtures and no model calls.

Run directly from the repository; an isolated source snapshot supplies all imports.
Fixtures test structural guards, never certify translations or real approvals.
"""
import copy
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


def note(english="A letter.", original="α", roman="alpha"):
    return ("---\ncategory: commentary\n---\n\n"
            "> [!quote]- John 1:1, synthetic fixture\n> " + original +
            "\n>\n> *" + roman + "*\n>\n> " + english + "\n")


def mark(text):
    return '<mark data-term="1">' + text + '</mark>'


class ContentBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="content-boundary-regression-")
        cls.home = Path(cls.temp.name)
        cls.prose = cls.home / ".agents/prose"
        shutil.copytree(ROOT / "runtime", cls.prose)
        shutil.copytree(ROOT / "authoring/prose", cls.prose, dirs_exist_ok=True)
        shutil.copytree(ROOT / "authoring/skills", cls.home / ".agents/skills")
        sys.path.insert(0, str(cls.prose))
        cls.scripture = importlib.import_module("scripture")
        cls.alignment = importlib.import_module("scripture_alignment")
        cls.handoff = importlib.import_module("handoff")
        cls.renderer = importlib.import_module("render_article")
        cls.review = importlib.import_module("review")
        cls.fixtures = importlib.import_module("test_pipeline")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(cls.prose))
        cls.temp.cleanup()

    def rendered(self, source):
        receipt = self.handoff.prepare(source)
        return "".join(self.renderer.render_source(item, receipt, {
            "languages": {"John 1:1, synthetic fixture": "grc"}})
            for item in self.renderer.source_items(source)
            if item["raw"][0].startswith("> [!"))

    def validate_markdown(self, source):
        path = self.home / "candidate.md"
        path.write_text(source)
        env = dict(os.environ, HOME=str(self.home), PYTHONPATH=str(self.prose))
        return subprocess.run([sys.executable, str(self.home / ".agents/skills/islamic-note/validate.py"), str(path)],
                              env=env, capture_output=True, text=True)

    def test_valid_scripture_round_trip(self):
        source = note()
        self.assertEqual(self.scripture.errors(source, "md"), [])
        self.assertEqual(self.scripture.errors(self.rendered(source), "html"), [])
        result = self.validate_markdown(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_extra_bible_arabic_rejected_in_markdown(self):
        source = note("A letter.\n>\n> كلام")
        self.assertTrue(self.scripture.errors(source, "md"))
        result = self.validate_markdown(source)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_extra_bible_arabic_rejected_in_html(self):
        source = note("A letter.\n>\n> كلام")
        self.assertTrue(self.scripture.errors(self.rendered(source), "html"))

    def test_source_script_cannot_masquerade_as_english(self):
        for translation in ["β", "דבר", "كلام"]:
            with self.subTest(translation=translation):
                source = note(translation)
                self.assertTrue(self.scripture.errors(source, "md"))
                self.assertTrue(self.scripture.errors(self.rendered(source), "html"))
                self.assertNotEqual(self.validate_markdown(source).returncode, 0)

    def test_scripture_allowed_inside_narration_commentary(self):
        source = note().replace("category: commentary", "category: narration").replace(
            "> [!quote]", "## Commentary\n\n> [!quote]")
        result = self.validate_markdown(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_whole_sentence_highlight_rejected(self):
        source = note(mark("This entire long sentence makes several separate claims about the passage and its interpretation."),
                      mark("α"), mark("alpha"))
        self.assertTrue(self.scripture.errors(source, "md"))
        self.assertTrue(self.scripture.errors(self.rendered(source), "html"))

    def test_short_english_lexical_expansion_allowed(self):
        for english in ["a woman", "his wife", "a married woman", "not yet"]:
            with self.subTest(english=english):
                source = note(mark(english), mark("γυνή"), mark("gynē"))
                self.assertEqual(self.scripture.errors(source, "md"), [])
                self.assertEqual(self.scripture.errors(self.rendered(source), "html"), [])

    def test_quran_standalone_pause_marks_are_not_words(self):
        self.assertEqual(self.alignment.words("أَحْيَاءٌ ۚ عِندَ رَبِّهِمْ ۖ يُرْزَقُونَ"),
                         ["أَحْيَاءٌ", "عِندَ", "رَبِّهِمْ", "يُرْزَقُونَ"])
        self.assertEqual(self.alignment.words("ۖ ۗ ۘ ۙ ۚ ۛ ١٦٩"), [])
        self.assertEqual(self.alignment.words("ʿindَ ʾā"), ["ʿindَ", "ʾā"])

    def test_alignment_accepts_reviewed_one_to_many_roman_span(self):
        source = note("For them.", "لَهُمُ", "la humu").replace("John 1:1", "Qur'an synthetic")
        record = self.alignment.prepare(source)
        record.update(status="approved", reviewer="synthetic-fidelity-agent")
        row = record["quotes"][0]
        row.update(status="passed", evidence="Synthetic coverage fixture checks one source word mapped to two displayed Roman tokens.",
                   units=[{"source_index": 0, "source": "لَهُمُ", "roman_start": 0,
                           "roman_end": 2, "romanization": "la humu"}])
        self.assertEqual(self.alignment.errors(source, record), [])
        omitted = copy.deepcopy(record)
        omitted["quotes"][0]["units"][0].update(roman_end=1, romanization="la")
        self.assertTrue(self.alignment.errors(source, omitted))

    def identity_fixture(self):
        fixture = self.fixtures.ReviewTests()
        draft = fixture.draft("A witness names four people.", "md")
        record = fixture.approved(draft)
        record["reviewer"] = "synthetic-primary"
        report = record["council"]["report"]
        for index, advisor in enumerate(report["advisors"]):
            advisor["reviewer"] = "synthetic-advisor-" + str(index)
        for index, peer in enumerate(report["peer_reviews"]):
            peer["reviewer"] = "synthetic-advisor-" + str(index)
        report["release"]["reviewer"] = "synthetic-advisor-0"
        self.rebind_synthetic_response(report)
        return draft, record

    def rebind_synthetic_response(self, report):
        response = json.loads(report["release"]["response"])
        response["council_sha256"] = self.review.council_digest(report)
        report["release"]["response"] = json.dumps(response)

    def test_distinct_advisors_and_resumed_advisor_release_allowed(self):
        draft, record = self.identity_fixture()
        self.assertEqual(self.review.verify(draft, draft, record), [])

    def test_duplicate_advisor_identity_rejected(self):
        draft, record = self.identity_fixture()
        report = record["council"]["report"]
        report["advisors"][1]["reviewer"] = report["advisors"][0]["reviewer"]
        self.rebind_synthetic_response(report)
        self.assertTrue(self.review.verify(draft, draft, record))

    def test_duplicate_peer_identity_rejected(self):
        draft, record = self.identity_fixture()
        report = record["council"]["report"]
        report["peer_reviews"][1]["reviewer"] = report["peer_reviews"][0]["reviewer"]
        self.rebind_synthetic_response(report)
        self.assertTrue(self.review.verify(draft, draft, record))

    def test_primary_cannot_supply_advisor_or_peer_response(self):
        for role in ["advisors", "peer_reviews"]:
            with self.subTest(role=role):
                draft, record = self.identity_fixture()
                report = record["council"]["report"]
                report[role][0]["reviewer"] = record["reviewer"]
                self.rebind_synthetic_response(report)
                self.assertTrue(self.review.verify(draft, draft, record))

    def test_primary_cannot_be_independent_release_reviewer(self):
        draft, record = self.identity_fixture()
        report = record["council"]["report"]
        report["release"]["reviewer"] = record["reviewer"]
        self.rebind_synthetic_response(report)
        self.assertTrue(self.review.verify(draft, draft, record))


if __name__ == "__main__":
    unittest.main()
