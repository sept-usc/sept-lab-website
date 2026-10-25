"""Deterministic no-network checks of deployment change notifications."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from tools import indexnow


HOST = "example.org"
KEY = "1234567890abcdef1234567890abcdef"
BASE = "https://" + HOST


def html(path="/", body="Original article", extra="", canonical=None):
    return (f'<html><head><title>Research</title><link rel="canonical" href="{canonical or BASE + path}">'
            f'<meta name="description" content="An introduction">{extra}</head>'
            f'<body><nav>Navigation</nav><main><h1>Research</h1><p>{body}</p></main>'
            '<footer>2026</footer><script>var build="old";</script></body></html>')


class IndexNowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.site = self.root / "public"
        self.site.mkdir()
        self.config = self.root / "indexnow.json"
        self.settings = {"host": HOST, "key": KEY}
        self.config.write_text(json.dumps(self.settings))
        self.state = self.root / "state.json"
        (self.site / (KEY + ".txt")).write_text(KEY + "\n")
        (self.site / "robots.txt").write_text("User-agent: *\nAllow: /\n")
        self.pages({"/": html()})
        self.argv = ["--site-dir", str(self.site), "--config", str(self.config), "--state", str(self.state)]

    def pages(self, pages):
        for path, text in pages.items():
            target = self.site / (path.lstrip("/") + ("index.html" if path.endswith("/") else ""))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        self.sitemap([BASE + path for path in pages])

    def sitemap(self, urls):
        rows = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
        (self.site / "sitemap.xml").write_text(f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>')

    def run_cli(self, *extra):
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            code = indexnow.main(self.argv + list(extra))
        return code, output.getvalue()

    def test_dry_run_is_deterministic_without_network_or_state_writes(self):
        with patch.object(indexnow, "urlopen", side_effect=AssertionError("network")):
            first = self.run_cli("--dry-run")
            self.assertEqual(first, self.run_cli("--dry-run"))
        self.assertEqual(first[0], 0)
        self.assertEqual(json.loads(first[1].splitlines()[0])["added"], [BASE + "/"])
        self.assertFalse(self.state.exists())

    def test_fingerprint_ignores_global_build_script_chrome_and_css_changes(self):
        before = html(body='A <a href="/paper/">paper</a><aside class="sidebar">Old sidebar</aside><svg><title>Diagram</title></svg>')
        after = before.replace("Navigation", "New navigation").replace("2026", "2027").replace('build="old"', 'build="new"').replace("Old sidebar", "New sidebar").replace('<h1>', '<h1 class="red">')
        self.assertEqual(indexnow.Page(before).fingerprint(), indexnow.Page(after).fingerprint())
        self.assertEqual(indexnow.Page(before).title, ["Research"])

    def test_fingerprint_covers_content_metadata_links_images_and_structured_data(self):
        before = html(body='A <a href="/paper/">paper</a><img src="/picture.png" alt="A plot">',
                      extra='<script type="application/ld+json">{"name":"Research"}</script>')
        for after in (before.replace("A plot", "A chart"), before.replace('/paper/', '/new/'),
                      before.replace("An introduction", "A new summary"), before.replace("A <a", "The <a"),
                      before.replace('{"name":"Research"}', '{"name":"New research"}')):
            with self.subTest(after=after):
                self.assertNotEqual(indexnow.Page(before).fingerprint(), indexnow.Page(after).fingerprint())

    def test_only_canonical_indexable_robot_allowed_sitemap_pages_are_eligible(self):
        self.pages({"/": html(), "/private/": html("/private/", extra='<meta name="robots" content="noindex,follow">'),
                    "/duplicate/": html("/duplicate/", canonical=BASE + "/"), "/blocked/": html("/blocked/")})
        (self.site / "robots.txt").write_text("User-agent: *\nDisallow: /blocked/\n")
        self.assertEqual(set(indexnow.snapshot(self.site, self.settings)), {BASE + "/"})

    def test_foreign_noncanonical_and_unsafe_urls_fail_before_network(self):
        for url in ("https://evil.example/", "http://example.org/", BASE + "/?q=x", BASE + "/#part", BASE + "/%2e%2e/a"):
            with self.subTest(url=url):
                self.sitemap([url])
                with patch.object(indexnow, "urlopen", side_effect=AssertionError("network")):
                    self.assertEqual(self.run_cli()[0], 1)

    def test_missing_main_or_empty_eligible_sitemap_cannot_trigger_mass_deletion(self):
        self.pages({"/": html().replace("<main>", "<section>").replace("</main>", "</section>")})
        self.assertEqual(self.run_cli("--dry-run")[0], 1)
        self.pages({"/": html(extra='<meta name="robots" content="none">')})
        self.assertEqual(self.run_cli("--dry-run")[0], 1)

    def test_no_change_does_not_fetch_key_or_notify(self):
        indexnow.write_state(self.state, HOST, indexnow.snapshot(self.site, self.settings))
        with patch.object(indexnow, "urlopen", side_effect=AssertionError("network")):
            code, output = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("No indexable content changes", output)

    def test_content_change_and_deletion_are_sent_once_after_key_verification(self):
        self.pages({"/": html(), "/old/": html("/old/")})
        indexnow.write_state(self.state, HOST, indexnow.snapshot(self.site, self.settings))
        self.pages({"/": html(body="Updated article"), "/new/": html("/new/")})
        calls = []
        with patch.object(indexnow, "verify_live_key", side_effect=lambda *a: calls.append("key")), \
                patch.object(indexnow, "submit", side_effect=lambda c, u: calls.append(u) or 200):
            code, output = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["key", [BASE + "/", BASE + "/new/", BASE + "/old/"]])
        self.assertIn("not guaranteed", output)
        self.assertEqual(indexnow.read_state(self.state, HOST), indexnow.snapshot(self.site, self.settings))

    def test_202_records_receipt_and_clearly_reports_validation_pending(self):
        with patch.object(indexnow, "verify_live_key"), patch.object(indexnow, "submit", return_value=202):
            code, output = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("key validation pending", output)
        self.assertTrue(self.state.exists())

    def test_notification_failure_preserves_retryable_state(self):
        indexnow.write_state(self.state, HOST, indexnow.snapshot(self.site, self.settings))
        original = self.state.read_bytes()
        self.pages({"/": html(body="New article")})
        with patch.object(indexnow, "verify_live_key"), patch.object(indexnow, "submit", side_effect=ValueError("HTTP 429")):
            code, output = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("429", output)
        self.assertEqual(self.state.read_bytes(), original)
        self.assertEqual(json.loads(self.run_cli("--dry-run")[1].splitlines()[0])["changed"], [BASE + "/"])

    def test_partial_batch_failure_saves_only_received_urls(self):
        current = {f"{BASE}/{n:05d}/": "a" * 64 for n in range(10001)}
        with patch.object(indexnow, "snapshot", return_value=current), patch.object(indexnow, "verify_live_key"), \
                patch.object(indexnow, "submit", side_effect=[200, ValueError("HTTP 429")]):
            self.assertEqual(self.run_cli()[0], 1)
        received = indexnow.read_state(self.state, HOST)
        self.assertEqual(set(received), set(sorted(current)[:10000]))
        self.assertEqual(indexnow.plan(current, received)["added"], [sorted(current)[-1]])

    def test_published_key_must_match_without_redirect_before_submission(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return KEY.encode()
            def geturl(self): return f"https://www.{HOST}/{KEY}.txt"
        with patch.object(indexnow, "urlopen", return_value=Response()), patch.object(indexnow, "submit") as send:
            self.assertEqual(self.run_cli("--key-attempts", "1")[0], 1)
            send.assert_not_called()
        Response.geturl = lambda self: f"https://{HOST}/{KEY}.txt"
        with patch.object(indexnow, "urlopen", return_value=Response()):
            indexnow.verify_live_key(self.settings, attempts=1)

    def test_retry_live_key_then_proceed(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return KEY.encode()
            def geturl(self): return f"https://{HOST}/{KEY}.txt"
        with patch.object(indexnow, "urlopen", side_effect=[OSError("CDN not ready"), Response()]) as fetch, \
                patch.object(indexnow.time, "sleep") as sleep:
            indexnow.verify_live_key(self.settings, attempts=2, delay=3)
        self.assertEqual(fetch.call_count, 2)
        sleep.assert_called_once_with(3)

    def test_actual_post_payload_and_response_codes(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
        for status in (200, 202, 204):
            Response.status = status
            with patch.object(indexnow, "urlopen", return_value=Response()) as fetch:
                if status == 204:
                    with self.assertRaises(ValueError): indexnow.submit(self.settings, [BASE + "/"])
                else:
                    self.assertEqual(indexnow.submit(self.settings, [BASE + "/"]), status)
                request = fetch.call_args.args[0]
                self.assertEqual(request.get_method(), "POST")
                self.assertEqual(request.full_url, indexnow.ENDPOINT)
                self.assertEqual(json.loads(request.data), {"host": HOST, "key": KEY,
                                 "keyLocation": f"{BASE}/{KEY}.txt", "urlList": [BASE + "/"]})
        for status in (400, 403, 422, 429, 500):
            with patch.object(indexnow, "urlopen", side_effect=HTTPError(indexnow.ENDPOINT, status, "failure", {"Retry-After": "60"}, io.BytesIO(b"error"))):
                with self.assertRaisesRegex(ValueError, f"HTTP {status}"):
                    indexnow.submit(self.settings, [BASE + "/"])

    def test_malformed_or_wrong_host_state_and_config_are_actionable_failures(self):
        for value in ([], {"version": 1, "host": "evil.example", "pages": {}},
                      {"version": 1, "host": HOST, "pages": {"https://evil.example/": "a" * 64}}):
            self.state.write_text(json.dumps(value))
            self.assertEqual(self.run_cli("--dry-run")[0], 1)
        self.state.unlink()
        self.config.write_text("[]")
        self.assertEqual(self.run_cli("--dry-run")[0], 1)


if __name__ == "__main__":
    unittest.main()
