"""Integration checks for discovery outputs against the site's actual content."""

import copy
import json
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build
import site_discovery


class HTMLSnapshot(HTMLParser):
    """Independently inspect rendered metadata and visible citation anchors."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.paper_ids = []
        self.canonicals = []
        self.markdown_links = []
        self.structured = []
        self._json = None
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "article" and "pub" in attrs.get("class", "").split():
            self.paper_ids.append(attrs["id"])
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs["href"])
        if tag == "link" and attrs.get("type") == "text/markdown":
            self.markdown_links.append(attrs["href"])
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._json = []

    def handle_data(self, data):
        if self._json is not None:
            self._json.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._json is not None:
            self.structured.append(json.loads("".join(self._json)))
            self._json = None


class DiscoveryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = build.load_all()
        cls.pages = build.render_all(cls.ctx)
        cls.html = {name: HTMLSnapshot(text) for name, text in cls.pages.items()
                    if name.endswith(".html")}
        cls.base = cls.ctx["site"]["base_url"].rstrip("/")
        cls.raw_publications = json.loads((ROOT / "data/publications.json").read_text())

    def graph(self, filename):
        self.assertEqual(len(self.html[filename].structured), 1, filename)
        data = self.html[filename].structured[0]
        self.assertEqual(data["@context"], "https://schema.org")
        return data["@graph"]

    def test_sitemap_has_the_eight_canonical_html_pages(self):
        filenames = {"index.html", "people.html", "research.html", "publications.html",
                     "teaching.html", "news.html", "join.html", "contact.html"}
        self.assertEqual(set(build.PAGES.values()), filenames)
        expected = {self.base + ("/" if name == "index.html" else "/" + name)
                    for name in filenames}
        root = ElementTree.fromstring(self.pages["sitemap.xml"])
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall("s:url/s:loc", ns)]
        self.assertEqual(len(urls), 8)
        self.assertEqual(set(urls), expected)
        self.assertFalse(root.findall(".//s:lastmod", ns), "No source modification dates exist")
        for name in filenames:
            expected_url = self.base + ("/" if name == "index.html" else "/" + name)
            self.assertEqual(self.html[name].canonicals, [expected_url])
            self.assertEqual(self.html[name].markdown_links, [name[:-5] + ".md"])
            self.graph(name)
        self.assertFalse(self.html["404.html"].canonicals)
        self.assertFalse(self.html["404.html"].structured)
        self.assertNotIn("404.md", self.pages)
        self.assertIn("Sitemap: " + self.base + "/sitemap.xml", self.pages["robots.txt"])

    def test_article_nodes_match_filtered_visible_papers_and_authors(self):
        source = self.raw_publications
        expected = [p for p in source["publications"] if p["year"] >= source["since"]]
        expected.sort(key=lambda pub: pub["year"], reverse=True)
        self.assertLess(len(expected), len(source["publications"]))
        graph = self.graph("publications.html")
        by_id = {node["@id"]: node for node in graph if "@id" in node}
        articles = [node for node in graph if node.get("@type") == "ScholarlyArticle"]
        self.assertEqual(self.html["publications.html"].paper_ids, [p["id"] for p in expected])
        self.assertEqual([node["@id"] for node in articles],
                         [self.base + "/publications.html#" + p["id"] for p in expected])
        for article, pub in zip(articles, expected):
            with self.subTest(paper=pub["id"]):
                self.assertEqual(article["name"], pub["title"])
                self.assertEqual(article["url"], pub["url"])
                authors = [author.get("name") or by_id[author["@id"]]["name"]
                           for author in article["author"]]
                self.assertEqual(authors, pub["authors"])
                self.assertIn(str(pub["year"]), article.get("description", ""))
                self.assertIn(pub["venue"], article.get("description", ""))
                for field in ("datePublished", "dateCreated", "dateModified"):
                    if field in article:
                        self.assertEqual(article[field], str(pub["year"]),
                                         "The data supplies only a year, never a month or day")

    def test_lab_and_pi_identity_links_are_separate(self):
        lab_github = self.ctx["site"]["links"]["github"]["url"]
        profiles = self.ctx["publications"]["profiles"]
        expected_profiles = {profiles[key] for key in ("scholar", "dblp") if profiles.get(key)}
        pi = self.ctx["people"]["pi"]
        for filename in build.PAGES.values():
            with self.subTest(page=filename):
                graph = self.graph(filename)
                lab = next(node for node in graph if node.get("@type") == "Organization"
                           and node.get("name") == self.ctx["site"]["name"])
                person = next(node for node in graph if node.get("@type") == "Person"
                              and node.get("name") == pi["name"])
                self.assertEqual(set(lab.get("sameAs", [])), {lab_github})
                self.assertEqual(set(person.get("sameAs", [])), expected_profiles)
                self.assertEqual(person["url"], pi["url"])
                self.assertEqual(person["jobTitle"], pi["title"])
                self.assertEqual(person["email"], pi["email"])
                self.assertNotIn("email", lab, "Only a named PI contact mailbox is supplied")

    def test_alumni_have_no_current_lab_affiliation(self):
        people = {node["name"]: node for node in self.graph("people.html")
                  if node.get("@type") == "Person"}
        for alumnus in self.ctx["people"]["alumni"]:
            with self.subTest(alumnus=alumnus["name"]):
                node = people[alumnus["name"]]
                for field in ("affiliation", "memberOf", "worksFor"):
                    self.assertNotIn(field, node)
        for group in self.ctx["people"]["groups"]:
            for member in group["members"]:
                with self.subTest(member=member["name"]):
                    node = people[member["name"]]
                    self.assertTrue(node.get("affiliation") or node.get("memberOf"))
                    if not member.get("url"):
                        self.assertNotIn("url", node)

    def test_research_directions_are_distinct_from_actual_project_nodes(self):
        graph = self.graph("research.html")
        theme_names = {theme["title"] for theme in self.ctx["research"]["themes"]}
        projects = self.ctx["research"]["projects"]
        project_names = {project["name"] for project in projects}
        self.assertTrue(theme_names.isdisjoint(project_names))
        project_nodes = [node for node in graph if node.get("name") in project_names]
        self.assertEqual({node["name"] for node in project_nodes}, project_names)
        for node in project_nodes:
            fragment = unquote(urlsplit(node["@id"]).fragment)
            self.assertIn(fragment, self.html["research.html"].ids)
            self.assertEqual(urlsplit(node["@id"]).path, "/research.html")
            self.assertEqual(node["url"], node["@id"])
        page = next(node for node in graph if node.get("@id") == self.base + "/research.html#webpage")
        directions = {node["name"] for node in page["about"] if node.get("@type") == "Thing"}
        self.assertEqual(directions, theme_names)
        for node in graph:
            if node.get("name") in theme_names:
                self.assertNotIn(node.get("@type"), ("Project", "ResearchProject"))
        items = page["mainEntity"]
        self.assertEqual(items["numberOfItems"], len(projects))
        self.assertEqual({item["item"]["@id"] for item in items["itemListElement"]},
                         {node["@id"] for node in project_nodes})

    def test_each_markdown_and_full_text_include_main_content_without_sidebar_or_game(self):
        full = self.pages["llms-full.txt"]
        for filename in build.PAGES.values():
            with self.subTest(page=filename):
                markdown = self.pages[filename[:-5] + ".md"]
                self.assertTrue(markdown.startswith("# "))
                self.assertIn("Canonical page: ", markdown)
                self.assertIn(markdown.strip(), full)
                self.assertNotIn(self.ctx["site"]["sidebar"]["news_title"], markdown)
                self.assertNotIn("SEPT Journey", markdown)
                self.assertNotIn("journey-themes", markdown)
                self.assertNotIn("Back to top", markdown)
                self.assertNotIn("<script", markdown)
        # Compare decoded text, so literal punctuation can be safely escaped in Markdown.
        text = {name: unescape(re.sub(r"\\([^\w\s])", r"\1", self.pages[name]))
                for name in ("research.md", "teaching.md", "people.md", "contact.md")}
        for project in self.ctx["research"]["projects"]:
            self.assertIn(project["name"], text["research.md"])
        for course in self.ctx["teaching"]["courses"]:
            self.assertIn(course["title"], text["teaching.md"])
        self.assertIn(self.ctx["people"]["pi"]["title"], text["people.md"])
        for line in self.ctx["contact"]["address"]:
            self.assertIn(line, text["contact.md"])

    def test_exports_follow_rendered_main_content_and_exclude_hidden_regions(self):
        # Sentinels demonstrate that exports follow rendered HTML rather than a separate
        # hand-maintained content list, and keep UI text outside the main column out.
        pages = dict(self.pages)
        for index, filename in enumerate(build.PAGES.values()):
            visible = "Discovery visible sentinel " + str(index)
            hidden = "Discovery hidden sentinel " + str(index)
            outside = "Discovery sidebar sentinel " + str(index)
            injection = ("<p>" + visible + "</p><dialog><p>" + hidden + "</p></dialog>"
                         "<script>" + hidden + "</script><span hidden>" + hidden + "</span>")
            pages[filename] = pages[filename].replace("</main>", injection + "</main>")
            pages[filename] = pages[filename].replace("</body>", "<aside>" + outside + "</aside></body>")
        exports = site_discovery.files(self.ctx, pages, build.PAGES)
        for index, filename in enumerate(build.PAGES.values()):
            markdown = exports[filename[:-5] + ".md"]
            self.assertIn("Discovery visible sentinel " + str(index), markdown)
            self.assertNotIn("Discovery hidden sentinel", markdown)
            self.assertNotIn("Discovery sidebar sentinel", markdown)
        self.assertNotIn("Discovery hidden sentinel", exports["llms-full.txt"])
        self.assertNotIn("Discovery sidebar sentinel", exports["llms-full.txt"])

    def test_literal_html_and_markdown_stay_literal_in_text_title_and_alt(self):
        pages = dict(self.pages)
        title = "Literal <title> [label] *word*"
        description = "Literal [description](https://unintended.example/) <tag>"
        literal = "<script>alert(1)</script> [x](https://unintended.example/) *plain* &copy;"
        alt = "<image> [alt] _plain_"
        injection = ("<h2>Literal [heading]</h2><p>" + escape(literal) + "</p>"
                     '<p><strong>real bold</strong> <em>real emphasis</em> '
                     '<a href="https://example.org/a(b)\\c?q=&amp;copy;&amp;x=1">real [link]</a></p>'
                     '<img src="assets/img/unused.png" alt="' + escape(alt, quote=True) + '">'
                     '<p><code>&lt;code&gt; `tick` *literal*</code></p>')
        pages["index.html"] = re.sub(r"<title>.*?</title>", "<title>" + escape(title) + "</title>",
                                     pages["index.html"], count=1)
        pages["index.html"] = re.sub(r'<meta name="description" content="[^"]*">',
                                     '<meta name="description" content="' + escape(description, quote=True) + '">',
                                     pages["index.html"], count=1)
        pages["index.html"] = pages["index.html"].replace("</main>", injection + "</main>")
        exports = site_discovery.files(self.ctx, pages, build.PAGES)
        markdown = exports["index.md"]
        self.assertTrue(markdown.startswith(r"# Literal &lt;title&gt; \[label\] \*word\*" + "\n"))
        self.assertIn(r"&lt;script&gt;alert\(1\)&lt;/script&gt; \[x\]\(https://unintended\.example/\) \*plain\* &amp;copy;", markdown)
        self.assertIn(r"&lt;image&gt; \[alt\] \_plain\_", markdown)
        self.assertIn(r"## Literal \[heading\]", markdown)
        self.assertIn("**real bold** *real emphasis*", markdown)
        self.assertIn(r"[real \[link\]](https://example.org/a%28b%29%5Cc?q=&amp;copy;&amp;x=1)", markdown)
        self.assertIn("``<code> `tick` *literal*``", markdown)
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("[x](https://unintended.example/)", markdown)
        self.assertIn(markdown.strip(), exports["llms-full.txt"])
        self.assertIn(r"[Literal &lt;title&gt; \[label\] \*word\*]", exports["llms.txt"])
        self.assertIn(r"Literal \[description\]\(https://unintended\.example/\) &lt;tag&gt;", exports["llms.txt"])

    def test_markdown_link_destinations_quote_delimiters_and_control_characters(self):
        target = 'https://example.org/a(b)\\c d\n\t\x01<>"?q=&copy;&x=1'
        self.assertEqual(site_discovery.markdown_destination(target),
                         'https://example.org/a%28b%29%5Cc%20d%0A%09%01%3C%3E%22?q=&amp;copy;&amp;x=1')

    def test_markdown_and_llms_local_links_resolve_to_generated_files_and_anchors(self):
        text_files = {name: text for name, text in self.pages.items()
                      if name.endswith(".md") or name in ("llms.txt", "llms-full.txt")}
        count = 0
        for filename, text in text_files.items():
            for target in re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", text):
                with self.subTest(source=filename, target=target):
                    parsed = urlsplit(target)
                    self.assertIn(parsed.scheme, ("https", "http", "mailto"))
                    if parsed.scheme == "mailto":
                        self.assertTrue(parsed.path)
                        continue
                    self.assertTrue(parsed.netloc)
                    if parsed.netloc != urlsplit(self.base).netloc:
                        continue
                    count += 1
                    path = unquote(parsed.path).lstrip("/") or "index.html"
                    self.assertIn(path, self.pages)
                    if parsed.fragment:
                        self.assertIn(path, self.html)
                        self.assertIn(unquote(parsed.fragment), self.html[path].ids)
        self.assertGreater(count, 20)
        guide = self.pages["llms.txt"]
        for filename in build.PAGES.values():
            self.assertIn(self.base + "/" + filename[:-5] + ".md", guide)
        self.assertIn(self.base + "/llms-full.txt", guide)

    def test_repeat_write_accepts_generated_metadata_and_refuses_unknown_note(self):
        with tempfile.TemporaryDirectory(prefix="sept-discovery-test-") as temporary:
            output = Path(temporary) / "site"
            build.write(self.pages, output)
            expected = {"robots.txt", "sitemap.xml", "llms.txt", "llms-full.txt"}
            expected.update(name[:-5] + ".md" for name in build.PAGES.values())
            for name in expected:
                self.assertEqual((output / name).read_text(), self.pages[name])
            build.write(self.pages, output)
            note = output / "personal-note.txt"
            note.write_text("Keep this user file.\n")
            original_index = (output / "index.html").read_text()
            with self.assertRaisesRegex(SystemExit, "personal-note\\.txt"):
                build.write(self.pages, output)
            self.assertEqual(note.read_text(), "Keep this user file.\n")
            self.assertEqual((output / "index.html").read_text(), original_index)

    def test_empty_base_url_does_not_claim_a_canonical_origin(self):
        ctx = copy.deepcopy(self.ctx)
        ctx["site"]["base_url"] = ""
        pages = build.render_all(ctx)
        for filename in build.PAGES.values():
            snapshot = HTMLSnapshot(pages[filename])
            self.assertFalse(snapshot.canonicals)
            self.assertFalse(snapshot.structured)
            self.assertNotIn("Canonical page: https://", pages[filename[:-5] + ".md"])
        root = ElementTree.fromstring(pages["sitemap.xml"])
        self.assertEqual(len(root), 0)
        self.assertNotIn("Sitemap:", pages["robots.txt"])


if __name__ == "__main__":
    unittest.main()
