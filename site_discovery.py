"""Search metadata and agent-readable exports from the site's validated content.

These files describe the same public pages; they do not promise indexing or ranking.
No generated dates, affiliations or publication status are inferred.
"""

import json
import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit
from xml.etree import ElementTree


SCHEMA = "https://schema.org"
MACHINE_FILES = {"robots.txt", "sitemap.xml", "llms.txt", "llms-full.txt"}
INDEXNOW_KEY_RE = re.compile(r"[a-f0-9]{32}")


def load_indexnow(root, site):
    """Load the optional public ownership key, scoped to the configured production host."""
    path = root / "indexnow.json"
    if not path.is_file():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ValueError("indexnow.json: could not read valid JSON ({})".format(exc)) from exc
    if not isinstance(config, dict) or set(config) != {"host", "key"}:
        raise ValueError("indexnow.json: expected only host and key fields")
    if not isinstance(config["key"], str) or not INDEXNOW_KEY_RE.fullmatch(config["key"]):
        raise ValueError("indexnow.json: key must contain 32 lowercase hexadecimal characters")
    if not isinstance(config["host"], str) or not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)+", config["host"]):
        raise ValueError("indexnow.json: host must be a lowercase DNS hostname")
    base = site.get("base_url") or ""
    if not isinstance(base, str) or not base:
        return {}  # A preview without a configured canonical origin publishes no ownership key.
    if config["host"] != urlsplit(base).netloc:
        raise ValueError("indexnow.json: host must match the base_url host in data/site.json")
    return config


def is_indexnow_key_file(path):
    """Recognize only a generated key whose filename and text agree, including an old key."""
    if path.suffix != ".txt" or INDEXNOW_KEY_RE.fullmatch(path.stem) is None or not path.is_file():
        return False
    try:
        return path.read_text(encoding="utf-8").strip() == path.stem
    except (UnicodeError, OSError):
        return False


def canonical(site, file_name):
    base = (site.get("base_url") or "").rstrip("/")
    if not base:
        return ""
    return base + ("/" if file_name == "index.html" else "/" + file_name)


def person_anchor(name):
    """A stable, readable fragment shared by the visible person and its schema identity."""
    return "person-" + "-".join(name.lower().split())


def plain(text):
    text = re.sub(r"\[([^\]]+)\]\([^\s]+\)", r"\1", text)
    return re.sub(r"\s+", " ", text.replace("**", "").replace("*", "")).strip()


def structured_data(ctx, page_id, title, description, url, project_anchor):
    """Use the filtered rendering context, including only papers visible on the site."""
    if not url:
        return None
    site, people = ctx["site"], ctx["people"]
    base = site["base_url"].rstrip("/")
    org_id, web_id = base + "/#lab", base + "/#website"
    pi = people["pi"]
    pi_id = base + "/people.html#" + quote(person_anchor(pi["name"]))
    org = {"@type": "Organization", "@id": org_id, "name": site["name"],
           "url": base + "/", "description": site["description"]}
    if site.get("expansion"):
        org["alternateName"] = site["expansion"] + " " + site.get("wordmark", {}).get("rest", "")
    mark = site.get("lockup", {}).get("mark")
    if mark:
        org["logo"] = urljoin(base + "/", mark)
    github = site.get("links", {}).get("github", {}).get("url")
    if github:
        org["sameAs"] = [github]
    department = site.get("links", {}).get("department", {})
    university = site.get("lockup", {}).get("affiliation")
    if department.get("label"):
        parent = {"@type": "Organization", "name": department["label"]}
        if department.get("url"):
            parent["url"] = department["url"]
        if university:
            parent["parentOrganization"] = {"@type": "CollegeOrUniversity", "name": university}
        org["parentOrganization"] = parent
    # The published contact is the PI's address, not a separately asserted lab mailbox.
    if pi.get("email"):
        org["contactPoint"] = {"@type": "ContactPoint", "name": pi["name"], "email": pi["email"]}
    themes = ctx["research"].get("themes", [])
    org["knowsAbout"] = [t["title"] for t in themes]
    person = {"@type": "Person", "@id": pi_id, "name": pi["name"],
              "affiliation": {"@id": org_id}}
    for source, target in (("url", "url"), ("title", "jobTitle"), ("email", "email")):
        if pi.get(source):
            person[target] = pi[source]
    profiles = ctx["publications"].get("profiles", {})
    if profiles:
        person["sameAs"] = [profiles[k] for k in ("scholar", "dblp") if profiles.get(k)]
    website = {"@type": "WebSite", "@id": web_id, "name": site["name"], "url": base + "/",
               "publisher": {"@id": org_id}, "inLanguage": "en"}
    kind = {"home": "WebPage", "contact": "ContactPage", "people": "CollectionPage",
            "research": "CollectionPage", "publications": "CollectionPage", "news": "CollectionPage"}.get(page_id, "WebPage")
    page = {"@type": kind, "@id": url + "#webpage", "url": url, "name": title,
            "description": description, "isPartOf": {"@id": web_id},
            "about": {"@id": org_id}, "inLanguage": "en"}
    graph = [org, website, person, page]
    if page_id == "home":
        page["mainEntity"] = {"@id": org_id}
    elif page_id == "people":
        ids = [pi_id]
        for current, rows in ((True, [m for g in people.get("groups", []) for m in g["members"]]),
                              (False, people.get("alumni", []))):
            for row in rows:
                item = {"@type": "Person", "@id": base + "/people.html#" + quote(person_anchor(row["name"])),
                        "name": row["name"]}
                if row.get("url"):
                    item["url"] = row["url"]
                if current:
                    item["affiliation"] = {"@id": org_id}
                    if row.get("role"):
                        item["jobTitle"] = row["role"]
                graph.append(item)
                ids.append(item["@id"])
        page["mainEntity"] = item_list(ids)
    elif page_id == "research":
        # Research directions are subjects, not projects or funded awards.
        page["about"] = [{"@id": org_id}] + [{"@type": "Thing", "@id": url + "#" + quote(t["id"]),
                                                "url": url + "#" + quote(t["id"]), "name": t["title"],
                                                "description": plain(t["summary"])} for t in themes]
        ids = []
        for project in ctx["research"].get("projects", []):
            pid = url + "#" + project_anchor(project)
            graph.append({"@type": "CreativeWork", "@id": pid, "url": pid,
                          "name": project["name"], "description": plain(project["description"])})
            ids.append(pid)
        if ids:
            page["mainEntity"] = item_list(ids)
    elif page_id == "publications":
        ids = []
        for pub in ctx["publications"]["publications"]:
            pid = url + "#" + pub["id"]
            authors = [{"@id": pi_id} if n == pi["name"] else {"@type": "Person", "name": n}
                       for n in pub["authors"]]
            # Data supplies a year, not a full publication date. Keep that precision in
            # the bibliographic description rather than inventing a month or day.
            graph.append({"@type": "ScholarlyArticle", "@id": pid, "name": pub["title"],
                          "headline": pub["title"], "url": pub["url"], "author": authors,
                          "description": "{} ({})".format(pub["venue"], pub["year"])})
            ids.append(pid)
        page["mainEntity"] = item_list(ids)
    return {"@context": SCHEMA, "@graph": graph}


def item_list(ids):
    return {"@type": "ItemList", "numberOfItems": len(ids), "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "item": {"@id": identifier}}
        for i, identifier in enumerate(ids)]}


def markdown_text(text):
    """Keep decoded HTML text literal; only the parser may introduce Markdown."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"([\\`*_{}\[\]()#+.!|~=\-])", r"\\\1", text)
    return escape(text, quote=False)


def markdown_destination(url):
    """Quote delimiter/control characters without changing URL separators."""
    return quote(url, safe=":/?#[]@!$&'*+,;=%-._~").replace("&", "&amp;")


def markdown_code(text):
    """Use a fence longer than any literal backtick run in an inline code span."""
    if not text:
        return ""
    fence = "`" * (max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    padding = " " if not text.isspace() and (text.startswith(("`", " ")) or text.endswith(("`", " "))) else ""
    return fence + padding + text + padding + fence


class MainMarkdown(HTMLParser):
    """Read only the rendered main column, omitting navigation, game and controls."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    BLOCK = {"p", "div", "section", "article", "ul", "ol", "details", "summary", "dl", "dt", "dd"}

    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url, self.title, self.description = url, "", ""
        self.in_title, self.in_main, self.skip = False, False, 0
        self.parts, self.links = [], []
        self.code = None

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta" and attr.get("name") == "description":
            self.description = attr.get("content", "")
        if tag == "main":
            self.in_main = True
            return
        if not self.in_main:
            return
        if self.skip:
            self.skip += tag not in self.VOID
            return
        classes = set(attr.get("class", "").split())
        if tag in {"script", "style", "svg", "button", "dialog", "h1"} or "hidden" in attr or attr.get("aria-hidden") == "true" or classes & {"visually-hidden", "screen-reader-text"}:
            self.skip = int(tag not in self.VOID)
            return
        if self.code is not None:
            if tag == "img" and attr.get("alt"):
                self.code.append(re.sub(r"\s+", " ", attr["alt"]))
            elif tag == "br":
                self.code.append(" ")
            return
        if tag in self.BLOCK or re.fullmatch(r"h[2-6]", tag):
            self.parts.append("\n\n")
        if re.fullmatch(r"h[2-6]", tag):
            self.parts.append("#" * int(tag[1]) + " ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "code":
            self.code = []
        elif tag == "a":
            self.links.append(markdown_destination(urljoin(self.url, attr.get("href", ""))))
            self.parts.append("[")
        elif tag == "img" and attr.get("alt"):
            self.parts.append(markdown_text(attr["alt"]))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "main":
            self.in_main = False
            return
        if not self.in_main:
            return
        if self.skip:
            self.skip -= 1
            return
        if self.code is not None and tag != "code":
            return
        if tag == "a" and self.links:
            self.parts.append("](" + self.links.pop() + ")")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "code":
            self.parts.append(markdown_code("".join(self.code or [])))
            self.code = None
        elif tag in self.BLOCK or re.fullmatch(r"h[2-6]", tag):
            self.parts.append("\n\n")

    def handle_data(self, text):
        if self.in_title:
            self.title += text
        if self.in_main and not self.skip:
            if self.code is not None:
                self.code.append(re.sub(r"\s+", " ", text))
            else:
                self.parts.append(markdown_text(text))

    def markdown(self):
        body = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in "".join(self.parts).splitlines())
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        source = "Canonical page: " + markdown_destination(self.url) + "\n\n" if self.url else ""
        return "# " + markdown_text(self.title).strip() + "\n\n" + source + body + "\n"


def files(ctx, pages, page_files):
    """Generate crawler metadata and text from the same eight indexable HTML pages."""
    site, base = ctx["site"], (ctx["site"].get("base_url") or "").rstrip("/")
    urls = [canonical(site, filename) for filename in page_files.values()]
    sitemap = ElementTree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in filter(None, urls):
        ElementTree.SubElement(ElementTree.SubElement(sitemap, "url"), "loc").text = url
    output = {"sitemap.xml": '<?xml version="1.0" encoding="utf-8"?>\n' + ElementTree.tostring(sitemap, encoding="unicode") + "\n",
              "robots.txt": "User-agent: *\nAllow: /\n" + ("\nSitemap: " + base + "/sitemap.xml\n" if base else "")}
    guide = ["# " + markdown_text(site["name"]), "", "> " + markdown_text(site["description"]), "",
             "Official lab pages. HTML is canonical; the Markdown copies and full text are generated from each page's main content.",
             "", "## Pages", ""]
    texts = []
    for page_id, filename in page_files.items():
        url = canonical(site, filename) or filename
        parser = MainMarkdown(url)
        parser.feed(pages[filename])
        parser.close()
        markdown_file = filename[:-5] + ".md"
        output[markdown_file] = parser.markdown()
        texts.append(output[markdown_file])
        md_url = base + "/" + markdown_file if base else markdown_file
        guide.append("- [{}]({}): {} [Markdown]({})".format(markdown_text(parser.title), markdown_destination(url),
                                                        markdown_text(parser.description), markdown_destination(md_url)))
    guide += ["", "## Full text", "", "- [All public pages]({})".format(markdown_destination(base + "/llms-full.txt" if base else "llms-full.txt")), ""]
    output["llms.txt"] = "\n".join(guide)
    output["llms-full.txt"] = "\n---\n\n".join(texts)
    config = ctx.get("indexnow") or {}
    if base and config:
        output[config["key"] + ".txt"] = config["key"] + "\n"
    return output
