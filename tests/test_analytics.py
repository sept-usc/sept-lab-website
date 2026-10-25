"""Check configuration/rendering and execute the real consent script without a network."""

import copy
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build


class Scripts(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.sources = []
        self.config = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.sources.append(attrs["src"])
            if attrs.get("id") == "analytics-script":
                self.config = attrs


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = build.load_all()

    def test_empty_measurement_id_has_no_analytics_loader_or_choice(self):
        ctx = copy.deepcopy(self.ctx)
        ctx["site"]["analytics"] = {"measurement_id": ""}
        for name, html in build.render_all(ctx).items():
            if not name.endswith(".html"):
                continue
            with self.subTest(page=name):
                self.assertNotIn("assets/js/analytics.js", Scripts(html).sources)
                self.assertNotIn('id="analytics-choice"', html)
                self.assertIn('id="privacy"', html)

    def test_configured_id_only_injects_local_loader_on_public_pages(self):
        ctx = copy.deepcopy(self.ctx)
        ctx["site"]["analytics"] = {"measurement_id": "G-TEST123456"}
        pages = build.render_all(ctx)
        for name in build.PAGES.values():
            with self.subTest(page=name):
                parsed = Scripts(pages[name])
                self.assertEqual(parsed.config["data-measurement-id"], "G-TEST123456")
                self.assertEqual(parsed.config["data-site-url"], ctx["site"]["base_url"])
                self.assertFalse(any("googletagmanager.com" in url or "google-analytics.com" in url for url in parsed.sources))
                self.assertIn('id="analytics-open"', pages[name])
                self.assertIn('id="analytics-allow"', pages[name])
                self.assertIn('id="analytics-decline"', pages[name])
        self.assertNotIn("assets/js/analytics.js", Scripts(pages["404.html"]).sources)
        self.assertNotIn('id="analytics-choice"', pages["404.html"])
        # Interactive consent UI remains outside the main-content agent exports.
        self.assertNotIn("Analytics choices", pages["index.md"])
        self.assertNotIn("Optional analytics", pages["llms-full.txt"])

    def test_measurement_id_validation_rejects_mistakes_and_markup(self):
        for value, valid in (("", True), ("G-TEST123456", True), ("AW-123456", False),
                             ('G-TEST\" onload=\"bad', False), ("G-LOWERcase", False)):
            with self.subTest(value=value):
                site = copy.deepcopy(self.ctx["site"])
                site["analytics"] = {"measurement_id": value}
                errors = build.DataErrors()
                with mock.patch.object(build, "load_json", return_value=site), mock.patch.object(build, "ERRORS", errors):
                    build.load_site()
                self.assertEqual(not errors.items, valid, errors.items)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the isolated consent-script tests")
    def test_consent_script(self):
        result = subprocess.run([shutil.which("node"), str(ROOT / "tests/analytics.test.js")],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
