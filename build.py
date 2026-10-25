#!/usr/bin/env python3
"""Build the SEPT Lab website.

Reads the content files in data/*.json, renders one HTML page per section
into dist/, and copies assets/ next to them. The layout is modeled on the
website of the Computer Security Group at ETH Zurich
(comsec.ethz.ch): a centered masthead, a menu bar, a main column with a news
and research sidebar, Karla throughout, and a vision image on the home page,
whose corner opens "the journey", a small game in a dialog (assets/js/journey.js).
The content schema supports optional sidebar, home.about, home.vision,
home.journey and research icon fields. All links are relative, so the output
works from file://, from any static host, and under a subpath such as
https://<user>.github.io/<repo>/.

Usage:
    python3 build.py            # build into dist/
    python3 build.py --check    # validate the data and render every page without writing files
    python3 build.py --out DIR  # build into DIR instead of dist/

The output directory is replaced on every build, so --out accepts only a new or
empty directory or one that holds nothing but an earlier build's output (HTML
pages, assets/ and the .nojekyll file every build writes).
To build a temporary preview:
    python3 build.py --out "$TMPDIR/sept-preview" && python3 tools/check_links.py "$TMPDIR/sept-preview"

Requires Python 3.9 or later and nothing outside the standard library.
"""

import argparse
import datetime
import difflib
import fnmatch
import html
import json
import re
import shutil
import sys
from html.parser import HTMLParser
import xml.parsers.expat
from xml.etree import ElementTree
from pathlib import Path, PurePosixPath
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"

# Files under assets/ that stay in the repository as sources but are not copied to dist/.
UNPUBLISHED_ASSETS = ("sept-logo-full.*", ".DS_Store")

PAGES = {
    # page id: output file
    "home": "index.html",
    "people": "people.html",
    "research": "research.html",
    "publications": "publications.html",
    "teaching": "teaching.html",
    "news": "news.html",
    "join": "join.html",
    "contact": "contact.html",
}
PUB_KINDS = {
    # kind: label used for the kind line in the meta column
    "conference": "Conference",
    "journal": "Journal",
    "workshop": "Workshop",
    "preprint": "Preprint",
    "thesis": "Thesis",
    "other": "Other",
}
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
# [label](url). The URL may contain one level of balanced parentheses, as in Wikipedia links.
LINK_RE = re.compile(r"\[([^\]\n]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")
SAFE_RELATIVE_RE = re.compile(r"[A-Za-z0-9._~/%#?&=+-]+")
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# Allowed fields for each kind of object in the data files. An unknown field is
# reported (with a suggestion), so a typo such as "pdf_url" for "pdf" cannot pass
# silently. Fields whose name starts with "_" are ignored and can hold comments.
KEYS = {
    "site": {"name", "wordmark", "expansion", "description", "base_url", "institution_short",
             "copyright", "lockup", "og_image", "nav", "links", "sidebar", "home_news_count", "home"},
    "wordmark": {"accent", "rest"},
    "lockup": {"mark", "mark_width", "mark_height", "affiliation"},
    "og_image": {"image", "alt", "width", "height"},
    "nav": {"page", "label", "emphasis"},
    "link": {"label", "url"},
    "action": {"label", "href"},
    "sidebar": {"news_title", "news_count", "research_title"},
    "home": {"title", "vision", "about", "lede", "actions", "featured", "journey"},
    "vision": {"image", "alt", "caption"},
    "journey": {"order"},
    "people": {"pi", "groups", "alumni"},
    "pi": {"name", "formal_name", "short_name", "role", "title", "url", "email"},
    "group": {"title", "members"},
    "member": {"name", "role", "note", "url"},
    "alumnus": {"name", "role", "years", "now", "note", "url"},
    "publications": {"profiles", "since", "publications"},
    "publication": {"id", "title", "authors", "venue", "venue_short", "year", "kind", "themes", "url", "pdf",
                    "code", "award", "equal_contribution", "links", "disclosures", "note"},
    "news": {"items"},
    "news_item": {"date", "slug", "category", "title", "body"},
    "research": {"headline", "intro", "thrusts", "themes", "projects"},
    "thrust": {"title", "text"},
    "theme": {"id", "title", "short", "layer", "summary", "topics", "topic_line", "description",
              "open_problems", "papers", "icon"},
    "project": {"name", "description", "paper", "themes", "links"},
    "teaching": {"intro", "courses"},
    "course": {"code", "title", "terms", "status", "description", "url"},
    "join": {"intro", "audiences", "include", "closing"},
    "audience": {"id", "title", "button", "subject", "body"},
    "include": {"title", "items"},
    "contact": {"intro", "address_title", "address", "address_source", "maps", "links"},
}
# Fields this design used to show and no longer reads, with what takes their place. They are reported
# with this hint instead of the plain "unknown field".
RETIRED = {
    ("home", "cta"): "the home page has no button any more; end home.about with a plain sentence that "
                     "links to join.html, such as \"We are looking for motivated PhD, MS, and undergraduate "
                     "students; see how to [join SEPT Lab](join.html).\"",
}


# ---------------------------------------------------------------------------
# Errors and validation
# ---------------------------------------------------------------------------

class DataErrors:
    """Collects every data problem so the user sees all of them at once."""

    def __init__(self):
        self.items = []

    def add(self, where, message):
        item = f"{where}: {message}"
        if item not in self.items:
            self.items.append(item)

    def raise_if_any(self):
        if self.items:
            lines = "\n".join(f"  - {item}" for item in self.items)
            sys.exit(f"build.py: the data files have {len(self.items)} problem(s):\n{lines}\n"
                     "Fix them and run python3 build.py again.")


ERRORS = DataErrors()
# Problems that do not stop the build; printed after it (and after --check).
WARNINGS = []


def load_json(name, kind):
    path = DATA / name
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.exit(f"build.py: missing data file {path.relative_to(ROOT)}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        sys.exit(f"build.py: data/{name}, line {exc.lineno}, column {exc.colno}: "
                 f"invalid JSON ({exc.msg}).")
    if not isinstance(data, dict):
        sys.exit(f"build.py: data/{name} must contain a JSON object ({{...}}) at the top level.")
    check_keys(data, kind, name)
    return data


def check_keys(obj, kind, where):
    """Report fields that the templates do not know about."""
    if not isinstance(obj, dict):
        return
    allowed = KEYS[kind]
    for key in obj:
        if key in allowed or key.startswith("_"):
            continue
        if (kind, key) in RETIRED:
            ERRORS.add(where, f"field {key!r} is retired: {RETIRED[(kind, key)]}")
            continue
        guess = difflib.get_close_matches(key, sorted(allowed), n=1)
        hint = f" (did you mean {guess[0]!r}?)" if guess else f"; allowed fields: {', '.join(sorted(allowed))}"
        ERRORS.add(where, f"unknown field {key!r}{hint}")


def expect(value, kind, where, required=True, allow_empty=False):
    """Check one value's type. kind is 'str', 'int', 'list', 'dict' or 'bool'."""
    types = {"str": str, "int": int, "list": list, "dict": dict, "bool": bool}
    if value is None:
        if required:
            ERRORS.add(where, f"is missing (expected {kind})")
        return False
    if kind == "int" and isinstance(value, bool):
        ERRORS.add(where, "expected a number, got true/false")
        return False
    if not isinstance(value, types[kind]):
        ERRORS.add(where, f"expected {kind}, got {type(value).__name__}")
        return False
    if kind == "str" and not allow_empty and required and not value.strip():
        ERRORS.add(where, "must not be empty")
        return False
    return True


def field(obj, key, kind, where, required=True, allow_empty=False, default=None):
    """Return obj[key] after a type check; record an error and return default otherwise."""
    if not isinstance(obj, dict):
        if obj is not None:
            ERRORS.add(where, f"expected an object {{...}}, got {type(obj).__name__}")
        return default
    value = obj.get(key)
    if value is None and not required:
        return default
    if expect(value, kind, f"{where}.{key}", required, allow_empty):
        return value
    return default


def positive_int(obj, key, where):
    value = field(obj, key, "int", where)
    if isinstance(value, int) and value < 1:
        ERRORS.add(f"{where}.{key}", "must be a positive number")
        return None
    return value


def objects(items, kind, where):
    """Yield (location, item) for each object in a list; report entries that are not objects."""
    for i, item in enumerate(items or []):
        item_where = f"{where}[{i}]"
        if isinstance(item, dict):
            check_keys(item, kind, item_where)
            yield item_where, item
        else:
            ERRORS.add(item_where, f"expected an object {{...}}, got {type(item).__name__}")


def check_url(url, where, local_ok=True):
    """Accept http(s), mailto, in-page anchors and relative paths; reject anything else."""
    if not isinstance(url, str) or not url.strip():
        ERRORS.add(where, "URL is empty")
        return
    # Browsers drop tabs and newlines inside URLs ("java\tscript:") and read "\\host" as
    # "//host", so these characters are never allowed.
    if re.search(r"[\x00-\x20\x7f-\x9f\\]", url):
        ERRORS.add(where, f"URL {url!r} contains whitespace, a control character or a backslash")
        return
    if re.match(r"^(https?://|mailto:)", url):
        return
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url) or url.startswith("//"):
        ERRORS.add(where, f"unsupported URL scheme in {url!r} (use https://, mailto: or a relative path)")
        return
    if not local_ok:
        ERRORS.add(where, f"expected an absolute https:// URL, got {url!r}")
        return
    if url.startswith("/"):
        ERRORS.add(where, f"use a relative link instead of {url!r} so the site works under a subpath")
        return
    if not SAFE_RELATIVE_RE.fullmatch(url):
        ERRORS.add(where, f"relative link {url!r} may contain only letters, digits and . _ ~ / % # ? & = + -")
        return
    if ".." in PurePosixPath(re.split(r"[?#]", url)[0]).parts:
        ERRORS.add(where, f"relative link {url!r} points outside the published site")


def url_field(obj, key, where, required=True, local_ok=True):
    """Read a URL field and validate it; optional fields may be missing or empty."""
    url = field(obj, key, "str", where, required=required, allow_empty=not required, default="")
    if url:
        check_url(url, f"{where}.{key}", local_ok)
    return url


def check_local_file(path, where):
    """A local image must be a file under assets/ that build() publishes."""
    if not path or not isinstance(path, str):
        return
    parts = PurePosixPath(path).parts
    if not path.startswith("assets/") or ".." in parts or "\\" in path:
        ERRORS.add(where, f"{path!r}: local files must live under assets/ so they are published")
        return
    if any(fnmatch.fnmatch(parts[-1], pattern) for pattern in UNPUBLISHED_ASSETS):
        ERRORS.add(where, f"{path!r} is a source file that is not published (see UNPUBLISHED_ASSETS in build.py)")
        return
    if not (ROOT / path).is_file():
        ERRORS.add(where, f"file {path!r} does not exist")


def check_markup(text, where):
    """Validate the links inside a text field that allows [label](url) markup."""
    if isinstance(text, str):
        for match in LINK_RE.finditer(text):
            check_url(match.group(2), where)


def check_markup_list(items, where):
    for i, text in enumerate(items or []):
        if expect(text, "str", f"{where}[{i}]"):
            check_markup(text, f"{where}[{i}]")


def check_links_list(items, where, local_ok=True):
    for link_where, link in objects(items, "link", where):
        field(link, "label", "str", link_where)
        url_field(link, "url", link_where, local_ok=local_ok)


def str_list(obj, key, where, required=True):
    """A list of non-empty strings; returns the valid strings."""
    items = field(obj, key, "list", where, required=required, default=[]) or []
    return [s for i, s in enumerate(items) if expect(s, "str", f"{where}.{key}[{i}]")]


def id_list(obj, key, where, known, what):
    """A list of ids that must name entries in KNOWN (for example theme ids); reports unknown
    and repeated ids and returns the list."""
    ids = str_list(obj, key, where, required=False)
    seen = set()
    for ref in ids:
        if ref in seen:
            ERRORS.add(f"{where}.{key}", f"{what} {ref!r} is listed twice")
        seen.add(ref)
        if known is not None and ref not in known:
            choices = ", ".join(sorted(known)) or "none defined"
            ERRORS.add(f"{where}.{key}", f"unknown {what} {ref!r}; choose from {choices}")
    return ids


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def esc(text):
    return html.escape(str(text), quote=True)


BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
ITALIC_RE = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")


TITLE_RE = re.compile(r"\b(Prof|Dr)\. ")


def tie(text):
    """A no-break space keeps a title with its name ("Prof. Li") at a line end."""
    return TITLE_RE.sub("\\1.\u00a0", text)


def curl(text):
    """Typographic apostrophes: a straight apostrophe between two letters becomes a curly one
    (Chekhov's -> Chekhov’s)."""
    return re.sub(r"(?<=\w)'(?=\w)", "\u2019", text)


def emphasis(text):
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    return tie(ITALIC_RE.sub(r"<em>\1</em>", text))


# Hyphenated words and identifiers, such as Low-Rank, Zero-Knowledge, TEE-based, AMD-SB-3036 or
# SEV-SNP. Browsers may break a line after a hyphen, which would split them as "Low-" / "Rank" or
# "AMD-SB-" / "3036". Tags in the text are matched first and left alone, so attribute values are
# never touched.
HYPHENATED_RE = re.compile(r"<[^>]*>|(?<![\w.-])[\w.]*\w(?:-\w[\w.]*)+(?![\w-])")


def keep_venues(text, ctx):
    """Join each short venue name from publications.json, and a year that follows it, with no-break
    spaces in already-escaped text, so a headline never ends with half a venue ("IEEE" / "S&P 2026").
    Apply it before keep_ids()."""
    venue_re = ctx.get("venue_re")
    if not venue_re:
        return text
    return venue_re.sub(lambda m: m.group(0).replace(" ", "\u00a0"), text)


# A link whose text is this short (in characters, at most three words) stays on one line, so a sentence
# never ends with a link split as "join" / "SEPT Lab." (the home page's recruiting sentence).
LINK_TIE = 24


def keep_link(label):
    """No-break spaces in a short link text (see LINK_TIE), before it is escaped."""
    if len(label) <= LINK_TIE and len(label.split()) <= 3:
        return label.replace(" ", "\u00a0")
    return label


def keep_ids(text):
    """Wrap hyphenated words of up to 24 characters in already-escaped text in a no-wrap span.
    Longer ones may still break at a hyphen, so they cannot push a narrow column wider."""
    def wrap(m):
        word = m.group(0)
        if word.startswith("<") or len(word) > 24:
            return word
        return f'<span class="nowrap">{word}</span>'
    return HYPHENATED_RE.sub(wrap, text)


def inline(text, where="text"):
    """Render the small markup allowed in data strings.

    [label](url) becomes a link, **text** bold and *text* italic. Everything
    else is HTML-escaped, so data can never inject markup. Links are swapped for
    placeholders before emphasis is applied, so * inside a URL stays literal and
    bold or italic text cannot overlap a link. A short link text stays on one line
    (keep_link()).
    """
    links = []

    def stash(match):
        url = match.group(2)
        check_url(url, where)
        links.append((keep_ids(emphasis(esc(curl(keep_link(match.group(1)))))), esc(url)))
        return f"\x00{len(links) - 1}\x00"

    out = keep_ids(emphasis(esc(curl(LINK_RE.sub(stash, str(text).replace("\x00", ""))))))
    return re.sub(r"\x00(\d+)\x00",
                  lambda m: '<a href="{1}">{0}</a>'.format(*links[int(m.group(1))]), out)


def paragraphs(items, where, cls=""):
    attr = f' class="{cls}"' if cls else ""
    return "\n".join(f"<p{attr}>{inline(p, f'{where}[{i}]')}</p>" for i, p in enumerate(items))


def join_names(names):
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


DATE_RE = re.compile(r"(\d{4})(?:-(0[1-9]|1[0-2])(?:-(0[1-9]|[12]\d|3[01]))?)?")


def parse_date(value, where):
    """Return (year, month, day) from 'YYYY', 'YYYY-MM' or 'YYYY-MM-DD'; 0 marks a missing part."""
    m = DATE_RE.fullmatch(value or "")
    if not m:
        ERRORS.add(where, f"date {value!r} must look like 2026, 2026-03 or 2026-03-22")
        return (0, 0, 0)
    year, month, day = int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0)
    if day:
        try:
            datetime.date(year, month, day)
        except ValueError:
            ERRORS.add(where, f"date {value!r} is not a real date")
            return (0, 0, 0)
    return (year, month, day)


def format_date(parts):
    year, month, day = parts
    if not month:
        return str(year)
    name = MONTHS[month - 1]
    if day:
        return f"{name} {day}, {year}"
    return f"{name} {year}"


def iso_date(parts):
    year, month, day = parts
    return f"{year}" + (f"-{month:02d}" if month else "") + (f"-{day:02d}" if day else "")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_site():
    site = load_json("site.json", "site")
    w = "site.json"
    for key in ("name", "description", "copyright", "institution_short"):
        field(site, key, "str", w)
    field(site, "expansion", "str", w, required=False, allow_empty=True, default="")
    url_field(site, "base_url", w, required=False, local_ok=False)

    wordmark = field(site, "wordmark", "dict", w, default={})
    check_keys(wordmark, "wordmark", f"{w}.wordmark")
    field(wordmark, "accent", "str", f"{w}.wordmark")
    field(wordmark, "rest", "str", f"{w}.wordmark", allow_empty=True)

    lockup = field(site, "lockup", "dict", w, default={})
    lw = f"{w}.lockup"
    check_keys(lockup, "lockup", lw)
    field(lockup, "mark", "str", lw)
    for key in ("mark_width", "mark_height"):
        positive_int(lockup, key, lw)
    check_local_file(lockup.get("mark"), f"{lw}.mark")
    field(lockup, "affiliation", "str", lw, required=False, allow_empty=True)

    og = field(site, "og_image", "dict", w, required=False, default=None)
    if og is not None:
        ow = f"{w}.og_image"
        check_keys(og, "og_image", ow)
        check_local_file(field(og, "image", "str", ow), f"{ow}.image")
        field(og, "alt", "str", ow)
        for key in ("width", "height"):
            positive_int(og, key, ow)

    pages_in_nav = set()
    for where, item in objects(field(site, "nav", "list", w, default=[]), "nav", f"{w}.nav"):
        page = field(item, "page", "str", where)
        field(item, "label", "str", where)
        field(item, "emphasis", "bool", where, required=False)
        if page and page not in PAGES:
            ERRORS.add(where, f"unknown page {page!r}; choose from {', '.join(PAGES)}")
        elif page in pages_in_nav:
            ERRORS.add(where, f"page {page!r} appears twice in the menu")
        pages_in_nav.add(page)
    for key, link in (field(site, "links", "dict", w, required=False, default={}) or {}).items():
        link_where = f"{w}.links.{key}"
        if not isinstance(link, dict):
            ERRORS.add(link_where, f"expected an object {{...}}, got {type(link).__name__}")
            continue
        check_keys(link, "link", link_where)
        field(link, "label", "str", link_where)
        url_field(link, "url", link_where)
    # An optional compatibility field; the sidebar uses its own news_count.
    count = field(site, "home_news_count", "int", w, required=False)
    if isinstance(count, int) and count < 0:
        ERRORS.add(f"{w}.home_news_count", "must be 0 or more")

    sidebar = field(site, "sidebar", "dict", w, required=False, default=None)
    if sidebar is not None:
        sw = f"{w}.sidebar"
        check_keys(sidebar, "sidebar", sw)
        for key in ("news_title", "research_title"):
            # A title names its widget's region, so it may be left out (for the default) but not blank.
            title = field(sidebar, key, "str", sw, required=False)
            if isinstance(title, str) and not title.strip():
                ERRORS.add(f"{sw}.{key}", "must not be empty; leave the field out to use the default title")
        n = field(sidebar, "news_count", "int", sw, required=False)
        if isinstance(n, int) and n < 0:
            ERRORS.add(f"{sw}.news_count", "must be 0 or more")

    home = field(site, "home", "dict", w, default={})
    hw = f"{w}.home"
    check_keys(home, "home", hw)
    field(home, "title", "str", hw, required=False)
    vision = field(home, "vision", "dict", hw, required=False, default=None)
    if vision is not None:
        vw = f"{hw}.vision"
        check_keys(vision, "vision", vw)
        # The file is read and checked in load_graphics(); an empty image means the default file.
        check_svg_file(field(vision, "image", "str", vw, required=False, allow_empty=True), f"{vw}.image")
        field(vision, "alt", "str", vw, required=False, allow_empty=True)
        check_markup(field(vision, "caption", "str", vw, required=False, allow_empty=True), f"{vw}.caption")
    # The About text ends with the recruiting sentence that links to the Join page (the home page has
    # no button; check_keys() reports the retired home.cta).
    check_markup_list(field(home, "about", "list", hw, required=False, default=[]), f"{hw}.about")
    # The lede is a fallback when home.about is missing. Optional action and featured
    # fields are validated for compatibility but are not rendered.
    check_markup(field(home, "lede", "str", hw, required=False), f"{hw}.lede")
    for aw, action in objects(field(home, "actions", "list", hw, required=False, default=[]), "action",
                              f"{hw}.actions"):
        field(action, "label", "str", aw)
        url_field(action, "href", aw)
    # Paper ids are checked against publications.json in load_all(), once both files are read.
    str_list(home, "featured", hw, required=False)
    # The journey's order of stops (README, "The journey"): the theme ids are checked against
    # research.json in cross_check(), once both files are read.
    journey = field(home, "journey", "dict", hw, required=False, default=None)
    if journey is not None:
        jw = f"{hw}.journey"
        check_keys(journey, "journey", jw)
        str_list(journey, "order", jw, required=False)
    return site


def load_people():
    people = load_json("people.json", "people")
    w = "people.json"
    pi = field(people, "pi", "dict", w, default={})
    pw = f"{w}.pi"
    check_keys(pi, "pi", pw)
    for key in ("name", "title"):
        field(pi, key, "str", pw)
    for key in ("formal_name", "short_name", "role", "email"):
        field(pi, key, "str", pw, required=False, allow_empty=True)
    url_field(pi, "url", pw, required=False)
    for gw, group in objects(field(people, "groups", "list", w, default=[]), "group", f"{w}.groups"):
        field(group, "title", "str", gw)
        for mw, member in objects(field(group, "members", "list", gw, default=[]), "member", f"{gw}.members"):
            field(member, "name", "str", mw)
            field(member, "role", "str", mw)
            check_markup(field(member, "note", "str", mw, required=False, allow_empty=True), f"{mw}.note")
            url_field(member, "url", mw, required=False)
    for aw, person in objects(field(people, "alumni", "list", w, default=[]), "alumnus", f"{w}.alumni"):
        field(person, "name", "str", aw)
        field(person, "role", "str", aw)
        for key in ("years", "now", "note"):
            field(person, key, "str", aw, required=False, allow_empty=True)
        check_markup(person.get("note"), f"{aw}.note")
        url_field(person, "url", aw, required=False)
    return people


def load_publications():
    data = load_json("publications.json", "publications")
    w = "publications.json"
    profiles = field(data, "profiles", "dict", w, required=False, default={}) or {}
    for key, url in profiles.items():
        check_url(url, f"{w}.profiles.{key}", local_ok=False)
    field(data, "since", "int", w, required=False)
    seen = set()
    for pw, pub in objects(field(data, "publications", "list", w, default=[]), "publication",
                           f"{w}.publications"):
        pid = field(pub, "id", "str", pw, default="")
        if pid:
            pw = f"{w} (id {pid})"
            if not SLUG_RE.fullmatch(pid):
                ERRORS.add(pw, "id may contain only lowercase letters, digits and hyphens")
            if pid in seen:
                ERRORS.add(pw, "duplicate id")
            seen.add(pid)
        for key in ("title", "venue", "venue_short"):
            field(pub, key, "str", pw)
        field(pub, "year", "int", pw)
        authors = field(pub, "authors", "list", pw, default=[])
        for j, a in enumerate(authors):
            expect(a, "str", f"{pw}.authors[{j}]")
        kind = field(pub, "kind", "str", pw, default="")
        if kind and kind not in PUB_KINDS:
            ERRORS.add(pw, f"kind {kind!r} must be one of {', '.join(PUB_KINDS)}")
        # Theme ids are checked against research.json in load_all(), once both files are read.
        id_list(pub, "themes", pw, None, "theme")
        url_field(pub, "url", pw)
        for key in ("pdf", "code"):
            url_field(pub, key, pw, required=False)
        field(pub, "award", "str", pw, required=False, allow_empty=True)
        check_markup(field(pub, "note", "str", pw, required=False, allow_empty=True), f"{pw}.note")
        for name in field(pub, "equal_contribution", "list", pw, required=False, default=[]):
            if name not in authors:
                ERRORS.add(pw, f"equal_contribution name {name!r} is not in the author list")
        check_links_list(field(pub, "links", "list", pw, required=False, default=[]), f"{pw}.links")
        check_links_list(field(pub, "disclosures", "list", pw, required=False, default=[]),
                         f"{pw}.disclosures", local_ok=False)
    return data


def load_news():
    data = load_json("news.json", "news")
    w = "news.json"
    seen = set()
    valid = []
    for iw, item in objects(field(data, "items", "list", w, default=[]), "news_item", f"{w}.items"):
        date = field(item, "date", "str", iw, default="")
        slug = field(item, "slug", "str", iw, default="")
        if slug and not SLUG_RE.fullmatch(slug):
            ERRORS.add(iw, "slug may contain only lowercase letters, digits and hyphens")
        field(item, "title", "str", iw)
        check_markup(field(item, "body", "str", iw), f"{iw}.body")
        field(item, "category", "str", iw, required=False, allow_empty=True)
        item["_date"] = parse_date(date, f"{iw}.date") if date else (0, 0, 0)
        year, month, _ = item["_date"]
        item["_id"] = f"{year}-{month:02d}-{slug}" if month else f"{year}-{slug}"
        if item["_id"] in seen:
            ERRORS.add(iw, f"duplicate news anchor {item['_id']!r}; change the slug")
        seen.add(item["_id"])
        valid.append(item)
    # Newest first. Items with only a year sort after dated items of the same year;
    # items with the same date keep their file order.
    valid.sort(key=lambda it: it["_date"], reverse=True)
    data["items"] = valid
    return data


def load_research(pub_ids):
    data = load_json("research.json", "research")
    w = "research.json"
    field(data, "headline", "str", w, required=False, allow_empty=True)
    check_markup(field(data, "intro", "str", w, required=False, allow_empty=True), f"{w}.intro")
    for tw, thrust in objects(field(data, "thrusts", "list", w, required=False, default=[]), "thrust",
                              f"{w}.thrusts"):
        field(thrust, "title", "str", tw, required=False, allow_empty=True)
        check_markup(field(thrust, "text", "str", tw), f"{tw}.text")
    seen = set()
    shorts = {}
    for tw, theme in objects(field(data, "themes", "list", w, default=[]), "theme", f"{w}.themes"):
        tid = field(theme, "id", "str", tw, default="")
        if tid:
            tw = f"{w} (theme {tid})"
            if not SLUG_RE.fullmatch(tid):
                ERRORS.add(tw, "id may contain only lowercase letters, digits and hyphens")
            if tid in seen:
                ERRORS.add(tw, f"duplicate theme id {tid!r}")
            seen.add(tid)
        for key in ("title", "short", "layer", "summary"):
            field(theme, key, "str", tw)
        short = theme.get("short")
        if isinstance(short, str) and short.strip():
            if short in shorts:
                ERRORS.add(tw, f"short label {short!r} is also used by theme {shorts[short]!r}")
            shorts[short] = tid
        str_list(theme, "topics", tw)
        # Optional compact topic text, retained for content compatibility.
        field(theme, "topic_line", "str", tw, required=False, allow_empty=True)
        check_markup_list(field(theme, "description", "list", tw, default=[]), f"{tw}.description")
        str_list(theme, "open_problems", tw, required=False)
        # Without an icon, the Research page uses assets/img/icons/<id>.svg when that file exists.
        check_svg_file(field(theme, "icon", "str", tw, required=False, allow_empty=True), f"{tw}.icon")
        for ref in id_list(theme, "papers", tw, None, "paper"):
            if ref not in pub_ids:
                ERRORS.add(f"{tw}.papers", f"paper id {ref!r} is not a published entry in publications.json "
                           "(missing, or older than 'since')")
    for pw, project in objects(field(data, "projects", "list", w, required=False, default=[]), "project",
                               f"{w}.projects"):
        field(project, "name", "str", pw)
        check_markup(field(project, "description", "str", pw), f"{pw}.description")
        ref = field(project, "paper", "str", pw, required=False, allow_empty=True)
        if ref and ref not in pub_ids:
            ERRORS.add(pw, f"paper id {ref!r} is not a published entry in publications.json "
                       "(missing, or older than 'since')")
        id_list(project, "themes", pw, seen, "theme")
        check_links_list(field(project, "links", "list", pw, required=False, default=[]), f"{pw}.links")
    return data


def load_teaching():
    data = load_json("teaching.json", "teaching")
    w = "teaching.json"
    check_markup(field(data, "intro", "str", w, required=False, allow_empty=True), f"{w}.intro")
    for cw, course in objects(field(data, "courses", "list", w, default=[]), "course", f"{w}.courses"):
        for key in ("code", "title"):
            field(course, key, "str", cw)
        for i, term in enumerate(field(course, "terms", "list", cw, default=[])):
            expect(term, "str", f"{cw}.terms[{i}]")
        field(course, "status", "str", cw, required=False, allow_empty=True)
        check_markup(field(course, "description", "str", cw, required=False, allow_empty=True),
                     f"{cw}.description")
        url_field(course, "url", cw, required=False)
    return data


def load_join():
    data = load_json("join.json", "join")
    w = "join.json"
    check_markup_list(field(data, "intro", "list", w, default=[]), f"{w}.intro")
    seen = set()
    for aw, aud in objects(field(data, "audiences", "list", w, default=[]), "audience", f"{w}.audiences"):
        aid = field(aud, "id", "str", aw, default="")
        if aid:
            if not SLUG_RE.fullmatch(aid):
                ERRORS.add(aw, "id may contain only lowercase letters, digits and hyphens")
            if aid in seen:
                ERRORS.add(aw, f"duplicate audience id {aid!r}")
            seen.add(aid)
        field(aud, "title", "str", aw)
        field(aud, "subject", "str", aw, required=False, allow_empty=True)
        # An optional compatibility field; contact details are rendered as text links.
        field(aud, "button", "str", aw, required=False, allow_empty=True)
        check_markup_list(field(aud, "body", "list", aw, default=[]), f"{aw}.body")
    include = field(data, "include", "dict", w, required=False, default=None)
    if include is not None:
        check_keys(include, "include", f"{w}.include")
        field(include, "title", "str", f"{w}.include")
        check_markup_list(field(include, "items", "list", f"{w}.include", default=[]), f"{w}.include.items")
    check_markup(field(data, "closing", "str", w, required=False, allow_empty=True), f"{w}.closing")
    return data


def load_contact():
    data = load_json("contact.json", "contact")
    w = "contact.json"
    check_markup(field(data, "intro", "str", w, required=False, allow_empty=True), f"{w}.intro")
    field(data, "address_title", "str", w, required=False, allow_empty=True)
    for i, line in enumerate(field(data, "address", "list", w, required=False, default=[])):
        expect(line, "str", f"{w}.address[{i}]")
    source = field(data, "address_source", "dict", w, required=False, default=None)
    if source is not None:
        sw = f"{w}.address_source"
        check_keys(source, "link", sw)
        field(source, "label", "str", sw)
        url_field(source, "url", sw)
    check_links_list(field(data, "maps", "list", w, required=False, default=[]), f"{w}.maps")
    check_links_list(field(data, "links", "list", w, required=False, default=[]), f"{w}.links")
    return data


# ---------------------------------------------------------------------------
# Inline SVG: the home page's vision image and the research directions' icons
# ---------------------------------------------------------------------------

SVG_NS = "{http://www.w3.org/2000/svg}"
SVG_URI = SVG_NS[1:-1]
# Namespaces whose elements a browser brings to life when someone opens the published master file
# itself (assets/ is copied to the site as it is).
LIVE_NS = {"http://www.w3.org/1999/xhtml", "http://www.w3.org/1998/Math/MathML"}
# The elements an inlined SVG may contain, compared as written, case included. The HTML parser that
# reads the page lowercases names and lets some HTML tags (img, p, meta, ...) end the drawing, so a
# list of what is allowed is checked rather than a list of what is not: script, style in capitals,
# foreignObject, iframe, a, the SMIL animation elements (which could change an attribute after the
# check) and every HTML tag are reported. A name with a prefix (sodipodi:namedview, rdf:RDF) is an
# inert unknown element in a page and stays allowed unless its namespace is XHTML or MathML.
SVG_ELEMENTS = {
    "svg", "g", "defs", "symbol", "use", "title", "desc", "style", "metadata",
    "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan", "textPath",
    "linearGradient", "radialGradient", "stop", "clipPath", "mask", "pattern", "marker", "image",
    "filter", "feBlend", "feColorMatrix", "feComponentTransfer", "feComposite", "feConvolveMatrix",
    "feDiffuseLighting", "feDisplacementMap", "feDistantLight", "feDropShadow", "feFlood", "feFuncA",
    "feFuncB", "feFuncG", "feFuncR", "feGaussianBlur", "feImage", "feMerge", "feMergeNode",
    "feMorphology", "feOffset", "fePointLight", "feSpecularLighting", "feSpotLight", "feTile",
    "feTurbulence"}
# Elements whose content the HTML parser reads as HTML (title and desc) or that hold CSS: text only.
SVG_TEXT_ONLY = {"title", "desc", "style"}
# The camelCase attribute names that the HTML parser restores after lowercasing (its table of SVG
# attributes); any other attribute name must be written in lower case, so that what the build checks
# and rewrites (id, class, style, href, on...) is what the browser sees.
SVG_CAMEL_ATTRS = {
    "attributeName", "attributeType", "baseFrequency", "baseProfile", "calcMode", "clipPathUnits",
    "diffuseConstant", "edgeMode", "filterUnits", "glyphRef", "gradientTransform", "gradientUnits",
    "kernelMatrix", "kernelUnitLength", "keyPoints", "keySplines", "keyTimes", "lengthAdjust",
    "limitingConeAngle", "markerHeight", "markerUnits", "markerWidth", "maskContentUnits", "maskUnits",
    "numOctaves", "pathLength", "patternContentUnits", "patternTransform", "patternUnits", "pointsAtX",
    "pointsAtY", "pointsAtZ", "preserveAlpha", "preserveAspectRatio", "primitiveUnits", "refX", "refY",
    "repeatCount", "repeatDur", "requiredExtensions", "requiredFeatures", "specularConstant",
    "specularExponent", "spreadMethod", "startOffset", "stdDeviation", "stitchTiles", "surfaceScale",
    "systemLanguage", "tableValues", "targetX", "targetY", "textLength", "viewBox", "viewTarget",
    "xChannelSelector", "yChannelSelector", "zoomAndPan"}
# CSS functions other than url() that load an image from a URL or a string; a drawing has no use for them.
CSS_FETCH_FUNC_RE = re.compile(r"(?<![\w-])((?:-webkit-)?(?:image-set|cross-fade)|image|src)\s*\(", re.I)
VISION_DEFAULT = "assets/img/vision.svg"
ICON_DIR = "assets/img/icons"
SVG_ID_RE = re.compile(r"""(\sid\s*=\s*)(["'])(.*?)\2""")
SVG_URL_REF_RE = re.compile(r"""url\(\s*(["']?)#([^)"'\s]+)\1\s*\)""")
SVG_HREF_REF_RE = re.compile(r"""(\s(?:xlink:)?href\s*=\s*)(["'])#(.*?)\2""")
SVG_ARIA_REF_RE = re.compile(r"""(\saria-(?:labelledby|describedby|controls|owns|flowto|details|"""
                             r"""activedescendant|errormessage)\s*=\s*)(["'])(.*?)\2""")
SVG_CLASS_RE = re.compile(r"""(\sclass\s*=\s*)(["'])(.*?)\2""")
SVG_STYLE_RE = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.S | re.I)
SVG_TITLE_RE = re.compile(r"<title\b[^>]*>.*?</title>\s*", re.S | re.I)
# url(...) in a style or an attribute may point only into the drawing itself or to an embedded image.
CSS_URL_RE = re.compile(r"""url\(\s*(["']?)([^"')]*)""", re.I)
# A selector in an inlined SVG's <style> may consist only of class and id selectors, each compound
# optionally followed by simple pseudo-classes, joined by combinators (".sv-lb", ".sv-lb .sv-nm",
# "#a > .b", ".sv-o:hover"), so after prefixing it can match nothing outside the drawing.
CSS_COMPOUND = r"(?:[.#]-?[_a-zA-Z][\w-]*)+(?::{1,2}[a-zA-Z-]+)*"
CSS_SELECTOR_RE = re.compile(CSS_COMPOUND + r"(?:\s*[\s>+~]\s*" + CSS_COMPOUND + r")*")


def css_url_problems(text):
    """Problems with references in CSS text (a <style> element, a style attribute or a presentation
    attribute such as fill): url(...) may point only to #fragments and data:image/ URLs, which keep the
    drawing self-contained; image-set(), cross-fade(), image() and src(), which load URLs from plain
    strings, are not allowed; and CSS escapes are not allowed next to a function call, because an
    escaped name ("\\75 rl(") is still a url() to the browser but not to these checks."""
    problems = []
    for m in CSS_URL_RE.finditer(text):
        target = m.group(2).strip()
        if not target.startswith(("#", "data:image/")):
            problems.append(f"uses url({target!r}); an inlined SVG may refer only to its own #ids "
                            "and to data:image/ URLs")
    for m in CSS_FETCH_FUNC_RE.finditer(text):
        problems.append(f"uses the CSS function {m.group(1).lower()}(), which can load other files; "
                        "use url(#id) or url(data:image/...)")
    if "\\" in text and "(" in text:
        problems.append("uses a CSS escape (\\) in CSS with a function call; write the CSS without escapes")
    return problems


def css_rule_problems(css):
    """Check the rules of an inlined SVG's <style> element: plain rules whose selectors are made of
    class and id selectors only, and @media blocks holding such rules. Anything else (element or
    universal selectors, attribute selectors, @font-face, @import, @keyframes) could style the page
    around the drawing, so it is reported."""
    problems = []
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"<!\[CDATA\[|\]\]>", "", css)
    problems.extend(css_url_problems(css))

    def rules(text):
        pos = 0
        while True:
            open_at = text.find("{", pos)
            semi = text.find(";", pos)
            if semi >= 0 and (open_at < 0 or semi < open_at):
                # A statement without a block: @import, @charset, @namespace or stray text.
                statement = text[pos:semi].strip()
                if statement:
                    what = (f"the CSS at-rule {statement.split()[0]!r}" if statement.startswith("@")
                            else f"CSS it cannot read ({statement[:40]!r})")
                    problems.append(f"uses {what} in its <style> element")
                pos = semi + 1
                continue
            if open_at < 0:
                if text[pos:].strip():
                    problems.append(f"has CSS it cannot read ({text[pos:].strip()[:40]!r})")
                return
            prelude = text[pos:open_at].strip()
            depth, k = 1, open_at + 1
            while k < len(text) and depth:
                depth += {"{": 1, "}": -1}.get(text[k], 0)
                k += 1
            if depth:
                problems.append("has unbalanced braces in its <style> element")
                return
            block = text[open_at + 1:k - 1]
            if prelude.startswith("@"):
                if re.match(r"@media\b", prelude, re.I):
                    rules(block)
                else:
                    problems.append(f"uses the CSS at-rule {prelude.split()[0]!r} in its <style> element")
            else:
                for selector in prelude.split(","):
                    if not CSS_SELECTOR_RE.fullmatch(selector.strip()):
                        problems.append(f"styles {selector.strip()!r} in its <style> element; use only class "
                                        "and id selectors, which the build can confine to the drawing")
                if "{" in block:
                    problems.append("nests rules inside a CSS rule in its <style> element")
            pos = k
    rules(css)
    return problems


def check_svg_file(path, where):
    """An inlined image must be an .svg file under assets/ that exists."""
    if not isinstance(path, str) or not path:
        return
    if not path.lower().endswith(".svg"):
        ERRORS.add(where, f"{path!r} must be an .svg file, because the build inlines it into the page")
        return
    check_local_file(path, where)


def svg_file_ok(path):
    return (isinstance(path, str) and path.startswith("assets/") and path.lower().endswith(".svg")
            and ".." not in PurePosixPath(path).parts and (ROOT / path).is_file())


def read_svg(path, where):
    """Read and check an SVG file. Returns a dict with the markup from <svg> to </svg> ("markup"), the
    text of the root's <title> ("title"), the id of the root's <desc> ("desc_id", "" without one) and
    the text of every <text> element ("texts"), or None after reporting why it cannot be inlined."""
    try:
        text = (ROOT / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        ERRORS.add(where, f"cannot read {path!r} as UTF-8 text ({exc})")
        return None
    if "<!ENTITY" in text:
        ERRORS.add(where, f"{path!r} declares XML entities; export it again as plain SVG without them")
        return None
    # Comments go first, so the checks below read exactly the text that is inlined.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    try:
        root = ElementTree.fromstring(text)
        raw = svg_markup(text)
    except (ElementTree.ParseError, xml.parsers.expat.ExpatError) as exc:
        ERRORS.add(where, f"{path!r} is not well-formed SVG ({exc})")
        return None
    if root.tag not in (SVG_NS + "svg", "svg") or raw["root"] != "svg":
        ERRORS.add(where, f"{path!r} must have <svg> as its root element")
        return None
    problems = list(raw["problems"])
    if not root.get("viewBox"):
        problems.append("has no viewBox attribute, so it cannot scale to the column")
    texts = []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        uri, _, tag = el.tag[1:].rpartition("}") if el.tag.startswith("{") else ("", "", el.tag)
        # The names as a browser reads the published file itself, namespaces resolved; svg_markup()
        # has checked them as the page's HTML parser reads them.
        if uri == SVG_URI and tag not in SVG_ELEMENTS:
            problems.append(f"contains a <{tag}> element, which an inlined SVG may not contain")
        elif uri in LIVE_NS:
            problems.append(f"contains a <{tag}> element of another document type ({uri})")
        if tag == "style":
            problems.extend(css_rule_problems("".join(el.itertext())))
        if tag == "text":
            texts.append(" ".join("".join(el.itertext()).split()))
    for problem in dict.fromkeys(problems):
        ERRORS.add(where, f"{path!r} {problem}")
    if problems:
        return None

    def child(name):
        found = root.find(SVG_NS + name)
        return found if found is not None else root.find(name)
    title, desc = child("title"), child("desc")
    return {"markup": raw["markup"],
            "title": " ".join("".join(title.itertext()).split()) if title is not None else "",
            "desc_id": (desc.get("id") or "") if desc is not None else "",
            "texts": texts}


def svg_markup(text):
    """Read an SVG's markup as the page's HTML parser will see it once inlined: names as written,
    without namespaces (which HTML ignores). Returns the root element's name ("root"), its markup
    from <svg to </svg> ("markup"), and the problems found ("problems"):

    - an element whose name is not in SVG_ELEMENTS exactly (case included; a prefixed name such as
      rdf:RDF is an inert unknown element and is allowed), or any element inside title, desc or style;
    - an attribute name in capitals other than the camelCase SVG names (SVG_CAMEL_ATTRS);
    - an event handler (any attribute named on..., with or without a prefix);
    - href or src (with or without a prefix) pointing anywhere but #id, or data:image/ outside <use>;
    - url(), image-set() and similar references to other files in any attribute (css_url_problems);
    - an xml-stylesheet processing instruction.
    Raises ExpatError for markup that is not well-formed."""
    data = text.encode("utf-8")
    parser = xml.parsers.expat.ParserCreate("utf-8")
    problems, stack = [], []
    found = {"root": None, "start": None, "end": None}

    def start(name, attrs):
        if found["root"] is None:
            found["root"], found["start"] = name, parser.CurrentByteIndex
        if stack and stack[-1] in SVG_TEXT_ONLY:
            problems.append(f"has a <{name}> element inside <{stack[-1]}>, which may contain only text")
        if ":" not in name and name not in SVG_ELEMENTS:
            problems.append(f"contains a <{name}> element, which an inlined SVG may not contain")
        stack.append(name)
        for key, value in attrs.items():
            local = key.rpartition(":")[2].lower()
            if key != key.lower() and key not in SVG_CAMEL_ATTRS:
                problems.append(f"has the attribute {key!r}; write attribute names in lower case "
                                "(except SVG's camelCase names such as viewBox)")
            if local.startswith("on"):
                problems.append(f"has an event handler attribute {key!r}")
            elif local in ("href", "src"):
                allowed = ("#",) if name == "use" else ("#", "data:image/")
                if not value.startswith(allowed):
                    problems.append(f"refers to another file ({value!r}); embed it or draw it in the SVG")
            if "(" in value:
                problems.extend(css_url_problems(value))

    def end(name):
        stack.pop()
        if not stack:
            close = data.find(b">", parser.CurrentByteIndex)
            found["end"] = close + 1 if close >= 0 else len(data)

    def instruction(target, _data):
        if target.lower() == "xml-stylesheet":
            problems.append("links a stylesheet (<?xml-stylesheet?>); put the styles in a <style> element")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.ProcessingInstructionHandler = instruction
    parser.Parse(data, True)
    markup = data[found["start"]:found["end"]].decode("utf-8") if found["end"] else ""
    return {"root": found["root"], "markup": markup, "problems": problems}


def scope_svg(markup, prefix):
    """Prefix the ids of an SVG (with the references to them: url(#...), href="#..." and aria-*
    id lists) and, when it has a <style> element, its class names and every class and id selector in
    that element, so that two inlined SVGs (or an SVG and the page) never share an id or a style rule.
    read_svg() has made sure that the selectors hold nothing but class and id selectors, so after
    this no rule of the drawing can match an element of the page."""
    ids = {m.group(3) for m in SVG_ID_RE.finditer(markup)}
    if ids:
        markup = SVG_ID_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{prefix}-{m.group(3)}{m.group(2)}", markup)
        markup = SVG_URL_REF_RE.sub(lambda m: f"url(#{prefix}-{m.group(2)})" if m.group(2) in ids else m.group(0),
                                    markup)
        markup = SVG_HREF_REF_RE.sub(lambda m: (f"{m.group(1)}{m.group(2)}#{prefix}-{m.group(3)}{m.group(2)}"
                                                if m.group(3) in ids else m.group(0)), markup)
        markup = SVG_ARIA_REF_RE.sub(lambda m: m.group(1) + m.group(2) + " ".join(
            f"{prefix}-{t}" if t in ids else t for t in m.group(3).split()) + m.group(2), markup)
    if "<style" in markup:
        markup = SVG_CLASS_RE.sub(lambda m: m.group(1) + m.group(2)
                                  + " ".join(f"{prefix}-{c}" for c in m.group(3).split()) + m.group(2), markup)

        def scope_css(m):
            return m.group(1) + prefix_selectors(m.group(2), prefix) + m.group(3)
        markup = SVG_STYLE_RE.sub(scope_css, markup)
    return markup


def prefix_selectors(css, prefix):
    """Prefix every class and id in the selectors of CSS text that css_rule_problems() accepted
    (plain rules and @media blocks); declarations such as fill:#abcdef stay as they are."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"<!\[CDATA\[|\]\]>", "", css)
    out, pos = [], 0
    while True:
        open_at = css.find("{", pos)
        if open_at < 0:
            out.append(css[pos:])
            return "".join(out)
        prelude = css[pos:open_at]
        depth, k = 1, open_at + 1
        while k < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        block = css[open_at + 1:k - 1]
        if prelude.strip().startswith("@"):
            out.append(f"{prelude}{{{prefix_selectors(block, prefix)}}}")
        else:
            out.append(re.sub(r"([.#])(-?[_a-zA-Z][\w-]*)", lambda c: f"{c.group(1)}{prefix}-{c.group(2)}", prelude)
                       + f"{{{block}}}")
        pos = k


def prune_aria_refs(markup):
    """Drop the ids that no longer exist (a <title> the build removed) from aria-labelledby and similar
    attributes inside an SVG, and the attribute when none is left."""
    ids = {m.group(3) for m in SVG_ID_RE.finditer(markup)}

    def keep(m):
        tokens = [t for t in m.group(3).split() if t in ids]
        return f"{m.group(1)}{m.group(2)}{' '.join(tokens)}{m.group(2)}" if tokens else ""
    return SVG_ARIA_REF_RE.sub(keep, markup)


def svg_root(markup, attrs):
    """Give the root <svg> the page's attributes instead of its own size, class, style, role and aria
    attributes. Without width and height it takes the width the stylesheet gives it and keeps the
    proportions of its viewBox."""
    m = re.match(r"""<svg\b((?:[^>"']|"[^"]*"|'[^']*')*?)(/?)>""", markup)
    own = re.sub(r"""\s(?:width|height|class|style|role|focusable|aria-[\w-]+)\s*=\s*(["']).*?\1""", "",
                 m.group(1), flags=re.I)
    return f"<svg{own} {attrs}{m.group(2)}>{markup[m.end():]}"


def check_layer_labels(ctx, texts, path):
    """The generated vision image labels its layers with the research.json theme `layer` values
    (design/vision/make_vision.py LABELS). A drawing with text labels must still name every layer,
    so renaming a layer in research.json without regenerating the drawing is noticed. A replacement
    without any <text> is not checked."""
    if not texts:
        return
    shown = " ".join(texts)
    themes = ctx["research"].get("themes")
    for theme in themes if isinstance(themes, list) else []:
        layer = theme.get("layer") if isinstance(theme, dict) else None
        if isinstance(layer, str) and layer.strip() and layer not in shown:
            WARNINGS.append(f"{path} does not label the layer {layer!r} of theme {theme.get('id')!r} "
                            "(research.json); regenerate the drawing (LABELS in design/vision/make_vision.py) "
                            "or update its text")


def load_graphics(ctx):
    """Read the SVGs the build inlines: the home page's vision image (site.json home.vision.image, by
    default assets/img/vision.svg) and each direction's icon (research.json theme icon, by default
    assets/img/icons/<theme id>.svg). Inlining lets the drawings use the page's web font. Replacing one
    of these files is enough to change the picture; a missing default file is simply left out."""
    site = ctx["site"]
    home = site.get("home") if isinstance(site.get("home"), dict) else {}
    vision = home.get("vision") if isinstance(home.get("vision"), dict) else {}
    ctx["vision"] = None
    explicit = vision.get("image") if isinstance(vision.get("image"), str) else ""
    if (explicit and svg_file_ok(explicit)) or (not explicit and (ROOT / VISION_DEFAULT).is_file()):
        where = "site.json.home.vision.image" if explicit else VISION_DEFAULT
        read = read_svg(explicit or VISION_DEFAULT, where)
        if read:
            markup = read["markup"]
            alt = vision.get("alt") if isinstance(vision.get("alt"), str) else ""
            label = " ".join((alt or read["title"]).split())
            if not label:
                ERRORS.add(where, "the vision image needs a text alternative: give the SVG a <title> "
                                  "or set site.json home.vision.alt")
            if alt:
                # The alt names the picture; the drawing's own <title> would only add a tooltip with
                # different words. The master file keeps it.
                markup = SVG_TITLE_RE.sub("", markup)
            attrs = f'class="vision__svg" role="img" aria-label="{esc(label)}"'
            if read["desc_id"]:
                # The root's <desc> is the long description, read after the short name.
                attrs += f' aria-describedby="vision-{esc(read["desc_id"])}"'
            # Without a caption field the caption is research.json headline; "" (or only spaces) hides
            # it. The caption is rendered here, once, and page_home() writes it as it is. The caption
            # field takes markup; the headline is plain text and gets only
            # the typographic touches (curly apostrophes, "Prof." tied to the name, unbroken hyphens).
            caption = vision.get("caption")
            if caption is None:
                headline = ctx["research"].get("headline")
                caption_html = (keep_ids(tie(esc(curl(headline))))
                                if isinstance(headline, str) and headline.strip() else "")
            else:
                caption_html = (inline(caption, "site.json.home.vision.caption")
                                if isinstance(caption, str) and caption.strip() else "")
            ctx["vision"] = {"svg": svg_root(prune_aria_refs(scope_svg(markup, "vision")), attrs),
                             "caption": caption_html}
            check_layer_labels(ctx, read["texts"], explicit or VISION_DEFAULT)
    ctx["icons"] = {}
    themes = ctx["research"].get("themes")
    for theme in themes if isinstance(themes, list) else []:
        tid = theme.get("id") if isinstance(theme, dict) else None
        if not isinstance(tid, str) or not tid:
            continue
        explicit = theme.get("icon") if isinstance(theme.get("icon"), str) else ""
        path = explicit or f"{ICON_DIR}/{tid}.svg"
        if not svg_file_ok(path):
            continue  # an explicit icon that is not usable has been reported by load_research()
        read = read_svg(path, f"research.json (theme {tid}).icon" if explicit else path)
        if read:
            # The icons are decorative (the direction's title follows), so they lose their tooltips.
            markup = SVG_TITLE_RE.sub("", read["markup"])
            ctx["icons"][tid] = svg_root(prune_aria_refs(scope_svg(markup, f"icon-{tid}")),
                                         'class="area__svg" aria-hidden="true" focusable="false"')


# ---------------------------------------------------------------------------
# Shared page frame
# ---------------------------------------------------------------------------

# Karla, regular and bold with italics, from Google Fonts with display=swap: the face of comsec.ethz.ch,
# whose layout this design follows.
FONTS = "https://fonts.googleapis.com/css2?family=Karla:ital,wght@0,400;0,700;1,400;1,700&amp;display=swap"
DOT = '<span class="sep" aria-hidden="true"> · </span>'
CHEVRON_UP = ('<svg class="chevron" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
              '<path d="M3.5 10.5 8 6l4.5 4.5" fill="none" stroke="currentColor" stroke-width="2.4" '
              'stroke-linecap="round" stroke-linejoin="round"/></svg>')
MENU_ICON = ('<svg class="menu-toggle__icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" '
             'focusable="false"><path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.6" '
             'stroke-linecap="round"/></svg>')


def pi_names(ctx):
    """Return the PI's plain name, formal name ('Prof. ...') and short name ('Prof. Li')."""
    pi = ctx["people"]["pi"]
    formal = pi.get("formal_name") or pi["name"]
    return pi["name"], formal, pi.get("short_name") or formal


def plural(n, word, words=None):
    return f"{n} {word if n == 1 else (words or word + 's')}"


def since_text(ctx):
    since = ctx["publications"].get("since")
    return f" since {since}" if since else ""


def head(ctx, page_id, title, description):
    """A page_id outside PAGES (the 404 page) gets no canonical URL and is kept out of search results.
    Every page links the same stylesheet and script; the home page's journey loads its own two files
    only when a reader asks for it (see JOURNEY_LINK)."""
    site = ctx["site"]
    base = (site.get("base_url") or "").rstrip("/")
    file_name = PAGES.get(page_id)
    if page_id == "home":
        full_title = site["home"].get("title") or f"{site['name']} · {title}"
    else:
        full_title = f"{title} · {site['name']}"
    meta = []
    if not file_name:
        meta.append('<meta name="robots" content="noindex">')
    elif base:
        page_url = f"{base}/" if page_id == "home" else f"{base}/{file_name}"
        meta.append(f'<link rel="canonical" href="{esc(page_url)}">')
        meta.append(f'<meta property="og:url" content="{esc(page_url)}">')
    og = site.get("og_image") or {}
    # Social platforms ignore relative image URLs, so the image is announced only
    # once base_url is known.
    if base and og.get("image"):
        meta.append(f'<meta property="og:image" content="{esc(base + "/" + og["image"])}">')
        meta.append(f'<meta property="og:image:width" content="{og["width"]}">')
        meta.append(f'<meta property="og:image:height" content="{og["height"]}">')
        meta.append(f'<meta property="og:image:alt" content="{esc(og["alt"])}">')
        meta.append('<meta name="twitter:card" content="summary_large_image">')
    else:
        meta.append('<meta name="twitter:card" content="summary">')
    meta_lines = "\n".join(meta)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#ffffff">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(site['name'])}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
{meta_lines}
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link rel="icon" type="image/png" sizes="32x32" href="assets/img/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="assets/img/icon-192.png">
<link rel="apple-touch-icon" href="assets/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="assets/css/style.css">
<script>document.documentElement.classList.add('js')</script>
<script src="assets/js/site.js" defer onerror="document.documentElement.classList.remove('js')"></script>
</head>"""


def brand_name(site):
    wordmark = site["wordmark"]
    rest = f" {esc(wordmark['rest'])}" if wordmark.get("rest") else ""
    return f'<span class="brand-accent">{esc(wordmark["accent"])}</span>{rest}'


def site_title(site):
    """The title under the lockup, in the place of comsec's "Computer Security Group": the expansion
    and the wordmark's second word ("Security, Privacy, and Trust Lab"), or the lab's name."""
    expansion = site.get("expansion") or ""
    if not expansion:
        return site["name"]
    return f"{expansion} {site['wordmark'].get('rest') or ''}".strip()


def site_title_html(site):
    """Highlight SE, P and T while keeping the full lab name as ordinary text."""
    title = site_title(site)
    expansion = "Security, Privacy, and Trust"
    if site.get("expansion") != expansion:
        return esc(title)
    return ('<span class="site-title__initial site-title__initial--gold">Se</span>curity, '
            '<span class="site-title__initial">P</span>rivacy, and '
            '<span class="site-title__initial site-title__initial--gold">T</span>rust'
            + esc(title[len(expansion):]))


def two_lines(text):
    """Split a short phrase into two lines of similar length ("University of" / "Southern California")."""
    words = text.split()
    if len(words) < 2:
        return [text]
    cut = min(range(1, len(words)), key=lambda i: max(len(" ".join(words[:i])), len(" ".join(words[i:]))))
    return [" ".join(words[:cut]), " ".join(words[cut:])]


def header(ctx, page_id):
    """The centered masthead: the lockup (the mark, the wordmark, a thin rule and the affiliation in two
    lines; together a link to the home page), the site title under it (the page's h1 on the home page,
    which has no other title), and the menu bar. Below 769 px the menu folds behind a Menu button while
    the html element has the js class, which the head script sets and removes again if site.js fails
    to load; without it the menu is a plain stacked list of links."""
    site = ctx["site"]
    lockup = site["lockup"]
    aff = lockup.get("affiliation") or ""
    aff_html = ""
    if aff:
        lines = " ".join(f'<span class="lockup__line">{esc(line)}</span>' for line in two_lines(aff))
        aff_html = (f'\n    <span class="lockup__rule" aria-hidden="true"></span>'
                    f'\n    <span class="lockup__inst">{lines}</span>')
    tag = "h1" if page_id == "home" else "p"
    title_label = f' aria-label="{esc(site_title(site))}"' if page_id == "home" else ""
    items = []
    for item in site["nav"]:
        current = ' aria-current="page"' if item["page"] == page_id else ""
        items.append(f'    <li><a href="{PAGES[item["page"]]}"{current}>{esc(item["label"])}</a></li>')
    return f"""<body class="page-{esc(page_id)}">
<a class="skip-link" href="#main">Skip to main content</a>
<header class="site-header" id="top">
  <a class="lockup" href="index.html">
    <img class="lockup__mark" src="{esc(lockup['mark'])}" width="{lockup['mark_width']}" height="{lockup['mark_height']}" alt="">
    <span class="lockup__name">{brand_name(site)}</span>{aff_html}
    <span class="visually-hidden">, home</span>
  </a>
  <{tag} class="site-title"{title_label}>{site_title_html(site)}</{tag}>
</header>
<nav class="site-nav" aria-label="Main">
  <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="menu">{MENU_ICON}<span>Menu</span></button>
  <ul class="menu" id="menu">
{chr(10).join(items)}
  </ul>
</nav>"""


def sidebar(ctx):
    """The sidebar of every page, as on comsec: the latest news headlines (site.json sidebar.news_count,
    default 8), each linking to its item on the News page, then the research directions, each linking
    to its section on the Research page. On phones it follows the main column."""
    site = ctx["site"]
    sb = site.get("sidebar") or {}
    widgets = []
    count = sb.get("news_count")
    items = ctx["news"]["items"][:8 if count is None else count]
    if items:
        title = (sb.get("news_title") or "").strip() or f"{site['wordmark']['accent']} news"
        lis = "\n".join(f'      <li><a href="news.html#{esc(it["_id"])}">'
                        f'{keep_ids(keep_venues(esc(curl(it["title"])), ctx))}</a></li>' for it in items)
        widgets.append(f"""  <section class="widget widget--news" aria-labelledby="w-news-h">
    <h2 class="widget-title" id="w-news-h">{esc(title)}</h2>
    <ul>
{lis}
    </ul>
  </section>""")
    themes = ctx["research"].get("themes") or []
    if themes:
        title = (sb.get("research_title") or "").strip() or "Research"
        lis = "\n".join(f'      <li><a href="research.html#{esc(t["id"])}">{keep_ids(esc(t["title"]))}</a></li>'
                        for t in themes)
        widgets.append(f"""  <section class="widget widget--research" aria-labelledby="w-research-h">
    <h2 class="widget-title" id="w-research-h">{esc(title)}</h2>
    <ul>
{lis}
    </ul>
  </section>""")
    if not widgets:
        return ""
    return '<aside class="sidebar" aria-label="Sidebar">\n' + "\n".join(widgets) + "\n</aside>"


def footer(ctx):
    """One line, as on comsec: the copyright on the left and a chevron back to the top on the right."""
    return f"""<footer class="site-footer">
  <div class="site-info">
    <p class="copyright">{esc(ctx['site']['copyright'])}</p>
    <a class="back-to-top" href="#top">{CHEVRON_UP}<span class="visually-hidden">Back to top</span></a>
  </div>
</footer>"""


def render_page(ctx, page_id, title, description, body, end=""):
    """The whole page: the head, the masthead and menu, the main column with the sidebar, and the
    footer. end is markup after the footer, right before </body>, outside the layout's containers: the
    home page's journey dialog."""
    frame = (f'<div class="site-content">\n<div class="inner">\n<main class="main" id="main" tabindex="-1">\n'
             f'{body}\n</main>\n{sidebar(ctx)}\n</div>\n</div>')
    parts = [head(ctx, page_id, title, description), header(ctx, page_id), frame, footer(ctx)]
    if end:
        parts.append(end)
    return "\n".join(parts) + "\n</body>\n</html>\n"


def page_title(text_html):
    return f'<h1 class="entry-title">{text_html}</h1>'


# ---------------------------------------------------------------------------
# Papers and other shared parts
# ---------------------------------------------------------------------------

def venue_label(pub):
    """The short venue with its year ("ISCA 2026", "Preprint 2026"), after a project's paper."""
    if pub["kind"] == "preprint":
        return f"Preprint {pub['year']}"
    if pub["kind"] == "thesis":
        return f"PhD Thesis {pub['year']}"
    return f"{pub['venue_short']} {pub['year']}"


def venue_text(pub):
    """The full venue without the short venue and year in parentheses at the end or before a comma
    ('... (ISCA 2026)', '... 38 (NeurIPS 2025), Creative AI Track'), or a leading 'arXiv preprint '
    or 'Ph.D. Dissertation, '. The tooltip of a short venue in a citation."""
    venue = pub["venue"].strip()
    venue = re.sub(r"^arXiv preprint ", "", venue)
    venue = re.sub(r"^Ph\.D\. Dissertation, ", "", venue)
    short = re.sub(r"\s*\([^()]*\b%d\)(?=,|$)" % pub["year"], "", venue)
    return short or venue


# The longest short venue whose words citation_venue() keeps together (twice as long for a full venue
# such as "arXiv preprint arXiv:2610.25611"); a longer one may still break, so that the venue and the
# year never make a run too wide for a phone's column.
VENUE_TIE = 16


def citation_venue(pub):
    """The venue sentence of a citation, as in the bibbase lists on comsec: "In *ISCA*, 2026." for
    conference, journal and workshop papers, keeping anything after the venue's parentheses
    ("In *NeurIPS*, Creative AI Track, 2025.") and marking workshops ("In *HASP* (workshop), 2025.");
    the short venue carries the full name as its tooltip. Preprints, theses and other entries show
    the full venue in italic ("*arXiv preprint arXiv:2610.25611*, 2026.").
    No-break spaces tie the year to the word before it and "In" to the venue, and keep a short venue
    of up to VENUE_TIE characters ("IEEE S&P", "ACM ASIACCS"), or a full venue of up to twice as many
    ("arXiv preprint arXiv:2610.25611"), on one line, so a citation never ends with the year alone or
    breaks as "In" / "HPCA", "ACM" / "ASIACCS" or "arXiv preprint" / "arXiv:2610.25611"."""
    venue = pub["venue"].strip()
    year = f' {pub["year"]}.'
    if pub["kind"] in ("conference", "journal", "workshop"):
        m = re.search(r"\([^()]*\)(,[^()]*)$", venue)
        extra = keep_ids(esc(m.group(1))) if m else ""
        short = pub["venue_short"]
        if pub["kind"] == "workshop" and "workshop" not in short.lower():
            extra = " (workshop)" + extra
        full = venue_text(pub)
        name = keep_ids(esc(short.replace(" ", " ") if len(short) <= VENUE_TIE else short))
        if full and full != short:
            name = f'<abbr title="{esc(full)}">{name}</abbr>'
        return f'In <em>{name}</em>{extra},{year}'
    if len(venue) <= 2 * VENUE_TIE:
        venue = venue.replace(" ", "\u00a0")
    return f'<em>{keep_ids(esc(venue))}</em>,{year}'


def display_title(pub):
    """The title with straight quotes turned into curly ones."""
    return curl(re.sub(r'"([^"]+)"', "“\\1”", pub["title"].strip()))


def short_title(pub):
    """The part before the first colon (the paper's name), or the whole title without its final period."""
    title = display_title(pub)
    return title.split(":", 1)[0] if ":" in title else title.rstrip(".")


def link_label(url, default):
    if "arxiv.org/abs/" in url:
        return "arXiv"
    return default


def lab_names(ctx):
    """Names of the PI, current members and alumni, which are shown in bold in author lists."""
    people = ctx["people"]
    names = {people["pi"]["name"]}
    names.update(m["name"] for g in people.get("groups", []) for m in g.get("members", []))
    names.update(a["name"] for a in people.get("alumni") or [])
    return names


def authors_html(pub, lab):
    """Authors with lab members in bold and an asterisk for equal contribution; no name breaks."""
    equal = set(pub.get("equal_contribution") or [])
    names = []
    for a in pub["authors"]:
        text = esc(a)
        if a in lab:
            text = f'<strong class="me">{text}</strong>'
        if a in equal:
            text += ('<sup class="eq" aria-hidden="true">*</sup>'
                     '<span class="visually-hidden"> (equal contribution)</span>')
        names.append(f'<span class="au">{text}</span>')
    return join_names(names)


def paper_link_items(pub):
    url = pub["url"]
    items = [("arXiv" if "arxiv.org/abs/" in url else "Paper", url)]
    if pub.get("pdf") and pub["pdf"] != url:
        items.append((link_label(pub["pdf"], "PDF"), pub["pdf"]))
    if pub.get("code"):
        items.append(("Code", pub["code"]))
    items.extend((link["label"], link["url"]) for link in pub.get("links") or [])
    items.extend((f"Vendor disclosure: {d['label']}", d["url"]) for d in pub.get("disclosures") or [])
    return items


def pub_entry(ctx, pub, lab, level=3, full=False):
    """One citation in the bibbase style of comsec's Publications page: the title in bold, the authors
    (lab members in bold), the venue sentence and any award in cardinal italic, then a row of small
    links. The title is a heading displayed inline, so screen-reader users can move between papers.
    full=True is the entry of the Publications page, with its anchor."""
    title = display_title(pub)
    end = "" if title.endswith((".", "?", "!")) else "."
    award = f' <em class="award">{esc(pub["award"])}</em>' if pub.get("award") else ""
    cite = (f'  <div class="pub__cite"><h{level} class="pub__title">{keep_ids(esc(title))}{end}</h{level}> '
            f'<span class="pub__authors">{authors_html(pub, lab)}.</span> '
            f'<span class="pub__venue">{citation_venue(pub)}</span>{award}</div>')
    # The hidden context keeps "Paper", "PDF" and "Code" apart in a screen reader's list of links.
    context = f'<span class="visually-hidden">: {esc(short_title(pub))}</span>'
    links = "".join(f'<li><a href="{esc(url)}">{keep_ids(esc(label))}{context}</a></li>'
                    for label, url in paper_link_items(pub))
    parts = [cite, f'  <ul class="pub__links" role="list">{links}</ul>']
    if pub.get("note"):
        parts.append(f'  <p class="pub__note">{inline(pub["note"], "publications.json.note")}</p>')
    body = "\n".join(parts)
    if not full:
        return f'<div class="pub">\n{body}\n</div>'
    return f'<article class="pub" id="{esc(pub["id"])}">\n{body}\n</article>'


def bold_note(pubs):
    any_eq = any(p.get("equal_contribution") for p in pubs)
    return "Lab members are shown in bold." + (" An asterisk (*) marks equal contribution." if any_eq else "")


def project_anchor(project):
    """The anchor of a project under "Projects and artifacts" (research.html#project-wave-artifact). Two
    projects whose names give the same anchor are reported by the rendered-id check."""
    return "project-" + (re.sub(r"[^a-z0-9]+", "-", project["name"].lower()).strip("-") or "unnamed")


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

# The walker of the journey game, drawn beside the link that opens
# the game: K is a pixel. It stands, and walks (two frames, the second a pixel lower) while pointed at.
WALKER_HEAD = ["..KKK..", ".KKKKK.", ".KKKKK.", ".KKKKK.", "..KKK..", "...K...", "..KKK.."]
WALKER = {
    "stand": WALKER_HEAD + [".K.K.K.", "K..K..K", "...K...", "..K.K..", ".K...K.", ".K...K."],
    "walk1": WALKER_HEAD + [".K.K.K.", "...K..K", "...K...", "..K.K..", ".K...K.", "K.....K"],
    "walk2": ["......."] + WALKER_HEAD + ["..KKK..", "...K...", "...K...", "..K.K..", "..K.K.."],
}


def pixel_path(rows):
    """The K pixels of a sprite as SVG path data, one subpath for each run of pixels in a row."""
    d = []
    for y, row in enumerate(rows):
        for m in re.finditer(r"K+", row):
            d.append(f"M{m.start()} {y}h{len(m.group())}v1h-{len(m.group())}z")
    return "".join(d)


# The journey's two files (README, "The journey"). The home page does not link them in its head: the
# link below names them, and site.js loads them, the stylesheet first, only when a reader points at
# the link, focuses or touches it, or opens index.html#journey.
JOURNEY_CSS = "assets/css/journey.css"
JOURNEY_JS = "assets/js/journey.js"
# The entry to the journey game: hidden until site.js shows it; the game's script then makes it open the
# dialog <dialog id="journey">.
JOURNEY_LINK = (f'<a class="journey-link" id="journey-open" href="#journey" aria-haspopup="dialog" '
                f'data-style-href="{JOURNEY_CSS}" data-script-src="{JOURNEY_JS}" hidden>'
                '<svg class="journey-link__fig" viewBox="0 0 7 13" width="7" height="13" fill="currentColor" '
                'aria-hidden="true" focusable="false">'
                + "".join(f'<path class="journey-link__{name}" d="{pixel_path(rows)}"/>' for name, rows in WALKER.items())
                + '</svg><span class="journey-link__text">Start the journey</span>'
                '<span class="journey-link__arrow" aria-hidden="true">&#8594;</span></a>')


def vision_figure(vision):
    """The home page's figure: the inlined drawing in a frame (.vision__art) that also holds, in the
    drawing's empty bottom corners, the button that pauses its motion and the link that opens the
    journey game, then the caption. site.js sets data-motion on the figure and reveals the button
    when the drawing has motion hooks and the reader has not asked for reduced motion; the game's
    script reveals the link. Without JavaScript both stay hidden and the drawing is still."""
    caption = ""
    if vision["caption"]:
        # Already HTML: load_graphics() rendered the markup.
        caption = f'\n  <figcaption class="vision__caption">{vision["caption"]}</figcaption>'
    return (f'<figure class="vision">\n  <div class="vision__art">\n  {vision["svg"]}\n'
            f'  <button class="vision__toggle" type="button" hidden>Pause animation</button>\n'
            f'  {JOURNEY_LINK}\n'
            f'  </div>{caption}\n</figure>')


def journey_entry(page):
    """The home page keeps the journey link only when it also holds the game's dialog (an element with
    the id "journey"), so the link can never point to a missing anchor."""
    if re.search(r"""\sid=["']journey["']""", page):
        return page
    return page.replace(f"\n  {JOURNEY_LINK}", "", 1)


# The journey (README, "The journey"): a pixel-map game in a modal
# dialog, which the link in the vision image's corner opens. The home page has the link and the dialog
# only when both of its files exist, so the site also builds without them; the game reads every word
# from the dialog: the directions as JSON in #journey-themes and the caption at the SEPT tree in the
# dialog's data-goal-* attributes.
JOURNEY_MAX_STOPS = 4   # the map lays out at most four directions; with more there is no journey
# Ids journey.js gives the parts it adds to the dialog; nothing else on the home page may use them.
JOURNEY_RUNTIME_IDS = ("journey-help", "journey-start-text", "journey-end-text")
NUMBER_WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]
CLOSE_ICON = ('<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
              '<path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="square"/></svg>')


def script_json(value):
    """JSON for a <script type="application/json"> element. <, > and & become \\u escapes, which
    JSON.parse reads back as the same characters, so no text in the data can end the element
    ("</script>") or open a comment ("<!--")."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def journey_files():
    """Which of the journey's two files exist under assets/."""
    return {path: (ROOT / path).is_file() for path in (JOURNEY_CSS, JOURNEY_JS)}


def journey_on(ctx):
    """Whether the home page carries the journey: both of its files exist, research.json has one to
    JOURNEY_MAX_STOPS themes, and the home page shows the vision image, whose frame holds the link
    that opens it. Otherwise the page links neither file and has no dialog, and journey_entry()
    removes the link. check_journey() says why when the journey is left out by mistake."""
    themes = ctx["research"].get("themes") or []
    return bool(ctx.get("vision")) and all(journey_files().values()) and 1 <= len(themes) <= JOURNEY_MAX_STOPS


def check_journey(ctx):
    """Warnings for a journey that is left out although its files are there (or one of them is): one
    file without the other, more themes than the map lays out, or no vision image to hold the link.
    Without either file the journey is simply off, and nothing is said."""
    files = journey_files()
    if not any(files.values()):
        return
    missing = [path for path, ok in files.items() if not ok]
    themes = ctx["research"].get("themes") or []
    if missing:
        WARNINGS.append(f"{missing[0]} is missing, so the home page has no journey; restore it, or remove "
                        f"{[p for p in files if p not in missing][0]} as well to turn the journey off")
    elif len(themes) > JOURNEY_MAX_STOPS:
        WARNINGS.append(f"research.json has {len(themes)} themes, but the journey's map lays out at most "
                        f"{JOURNEY_MAX_STOPS}, so the home page has no journey (and no link to it)")
    elif themes and not ctx.get("vision"):
        WARNINGS.append("the home page shows no vision image, whose corner holds the journey's link, so the "
                        "home page has no journey")


def journey_themes(ctx):
    """The themes in the order of the journey's stops: site.json home.journey.order when it is set
    (cross_check() has made sure it lists every theme id of research.json once), else research.json's
    order. Only the game follows it; the vision image, the Research page and the sidebar keep
    research.json's order."""
    themes = ctx["research"].get("themes") or []
    order = (ctx["site"]["home"].get("journey") or {}).get("order")
    if not order:
        return list(themes)
    by_id = {t["id"]: t for t in themes}
    return [by_id[ref] for ref in order]


def journey_records(ctx):
    """The directions for the game, in the journey's order (journey_themes()), each with its
    representative papers resolved in publications.json: the paper's short name, its short venue
    ("Preprint" for a preprint, "PhD Thesis" for a thesis, as venue_label() writes them) and year, and
    its entry on the Publications page. The game shows the first two papers; short and topic_line are
    carried in the game data but not shown."""
    def paper(pub):
        venue = {"preprint": "Preprint", "thesis": "PhD Thesis"}.get(pub["kind"], pub["venue_short"])
        return {"title": short_title(pub), "venue_short": venue, "year": pub["year"],
                "href": f"{PAGES['publications']}#{pub['id']}"}
    return [{"id": t["id"], "title": t["title"], "short": t["short"], "layer": t["layer"],
             "summary": t["summary"], "topic_line": t.get("topic_line") or " · ".join(t["topics"][:3]),
             "href": f"{PAGES['research']}#{t['id']}",
             "papers": [paper(ctx["pubs_by_id"][r]) for r in t.get("papers") or []]}
            for t in journey_themes(ctx)]


def journey_dialog(ctx):
    """The game's modal dialog, written once on the home page after the footer, outside the layout's
    containers. The title line is the wordmark's accent and "Journey" ("SEPT Journey"); under it the
    number of directions and the layers of the first and last stop as written (journey_themes()), as the
    game's cards name them ("Four research directions, from Hardware to Agents"), so a layer such as
    "AI agents" keeps its capitals.
    The data-goal-* attributes give the caption at the SEPT tree, where the walk ends (the lab's name,
    "<expansion> at <institution_short>." and the Research page's headline), and the ending card's
    links (the Research and Publications pages). journey.js adds the map, the bar and the caption
    inside #journey-game, and a Sound toggle before the close button."""
    site = ctx["site"]
    themes = journey_themes(ctx)
    layers = [t["layer"] for t in themes]
    sub = f"{NUMBER_WORDS[len(themes)]} research direction{'s' if len(themes) != 1 else ''}"
    if len(layers) > 1:
        sub += f", from {layers[0]} to {layers[-1]}"
    goal_text = f"{site['expansion']} at {site['institution_short']}." if site.get("expansion") else ""
    headline = (ctx["research"].get("headline") or "").strip()
    attrs = (f' data-goal-title="{esc(site["name"])}"' + (f' data-goal-text="{esc(goal_text)}"' if goal_text else "")
             + (f' data-goal-lead="{esc(headline)}"' if headline else "")
             + f' data-goal-href="{PAGES["research"]}" data-papers-href="{PAGES["publications"]}"')
    return f"""<dialog class="journey" id="journey" aria-labelledby="journey-title" aria-describedby="journey-sub"{attrs}>
  <div class="journey__head">
    <div class="journey__heading">
      <h2 class="journey__title" id="journey-title">{esc(site["wordmark"]["accent"])} Journey</h2>
      <p class="journey__sub" id="journey-sub">{esc(sub)}</p>
    </div>
    <button class="journey__close" type="button" data-journey-close>{CLOSE_ICON}<span class="visually-hidden">Close</span></button>
  </div>
  <div class="journey__game" id="journey-game"></div>
  <script type="application/json" id="journey-themes">{script_json(journey_records(ctx))}</script>
</dialog>"""


def page_home(ctx):
    """comsec's front page with the vision image in the place of the group photo: the image (with the
    journey's link in its corner), a short rule, and the About paragraphs (site.json home.about, or
    home.lede without them), the last of which says that the lab is recruiting and links to the Join
    page. The sidebar follows as on every page, and the journey's dialog after the footer.
    home.actions and home.featured stay valid in the data but are not shown."""
    site = ctx["site"]
    home = site["home"]
    parts = []
    vision = ctx.get("vision")
    if vision:
        parts.append(vision_figure(vision) + '\n<hr class="separator">')
    # The lede stands in only when about is missing (or null); an empty list shows no text.
    about = home.get("about")
    if about is None:
        about = [home["lede"]] if home.get("lede") else []
    if about:
        parts.append(f'<h2 class="visually-hidden">About {esc(site["name"])}</h2>\n'
                     + paragraphs(about, "site.json.home.about"))
    body = '<div class="content content--home">\n' + "\n".join(parts) + "\n</div>"
    if journey_on(ctx):
        page = render_page(ctx, "home", site["institution_short"], site["description"], body,
                           end=journey_dialog(ctx))
        for rid in JOURNEY_RUNTIME_IDS:
            if re.search(rf"""\sid=["']{rid}["']""", page):
                ERRORS.add("rendered index.html", f"id {rid!r} is reserved for the parts journey.js adds")
    else:
        page = render_page(ctx, "home", site["institution_short"], site["description"], body)
    return journey_entry(page)


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

def page_research(ctx):
    """comsec's research page: per direction a row with the icon on the left and, on the right, the
    title as a cardinal link (an anchor to the section) and the summary; under the row, across the
    column, the description, the topics, the open problems, the representative papers and a link to
    the direction's papers on the Publications page. Without an icon the row is the text alone.
    "Projects and artifacts" follows as a plain list. research.json intro and thrusts stay valid but
    are not shown, because the home page's About text already states the mission and the thrusts;
    headline is the home page's vision caption."""
    site = ctx["site"]
    research = ctx["research"]
    themes = research.get("themes") or []
    projects = research.get("projects") or []
    lab = lab_names(ctx)
    sections = []
    for t in themes:
        tid = esc(t["id"])
        n = len(ctx["theme_papers"][t["id"]])
        rep = [ctx["pubs_by_id"][r] for r in t.get("papers") or []]
        parts = [paragraphs(t["description"], "research.json.themes." + t["id"]),
                 f'    <p class="area__topics"><strong>Topics:</strong> {keep_ids(esc(", ".join(t["topics"])))}.</p>']
        if t.get("open_problems"):
            items = "".join(f"<li>{keep_ids(esc(x))}</li>" for x in t["open_problems"])
            parts.append(f'    <h3 class="area__h">Open problems</h3>\n    <ul class="area__problems">{items}</ul>')
        if rep:
            rows = "\n".join(pub_entry(ctx, p, lab, level=4) for p in rep)
            parts.append(f'    <h3 class="area__h">Representative papers</h3>\n    <div class="pubs pubs--area">\n{rows}\n    </div>')
        if n:
            # Every paper of the direction, newest first, folded under one line; each item links to
            # its entry on the Publications page.
            hidden = f'<span class="visually-hidden">: {esc(t["title"])}</span>'
            items = "".join(f'<li><a href="{PAGES["publications"]}#{esc(p["id"])}">{keep_ids(esc(short_title(p)))}</a>, '
                            f'{esc(venue_label(p))}</li>' for p in ctx["theme_papers"][t["id"]])
            parts.append(f'    <details class="area__more">\n      <summary>All {plural(n, "paper")} in this direction'
                         f'{since_text(ctx)}{hidden}</summary>\n      <ul class="area__all">{items}</ul>\n    </details>')
        icon = ctx["icons"].get(t["id"], "")
        # comsec's row (icon, title, summary), then the longer text across the whole column.
        icon_html = f'\n    <div class="area__icon">{icon}</div>' if icon else ""
        cls = "area" if icon else "area area--no-icon"
        body = "\n".join(parts)
        sections.append(f"""<section class="{cls}" id="{tid}" aria-labelledby="{tid}-title">
  <div class="area__row">{icon_html}
    <div class="area__head">
      <h2 class="area__title" id="{tid}-title"><a href="#{tid}">{keep_ids(esc(t['title']))}</a></h2>
      <p class="area__summary">{keep_ids(esc(t["summary"]))}</p>
    </div>
  </div>
  <div class="area__details">
{body}
  </div>
</section>""")
    if projects:
        github = (site.get("links") or {}).get("github")
        more = ""
        if github:
            shown = re.sub(r"^https?://", "", github["url"]).rstrip("/")
            more = (f'\n  <p>These and other repositories are in the lab’s GitHub organization, '
                    f'<a href="{esc(github["url"])}">{esc(shown)}</a>.</p>')
        items = []
        for i, p in enumerate(projects):
            name = esc(p["name"])
            text = [f'<strong class="project__name">{keep_ids(name)}</strong>.',
                    inline(p["description"], f"research.json.projects[{i}]")]
            if p.get("paper"):
                pub = ctx["pubs_by_id"][p["paper"]]
                text.append(f'Paper: <a href="publications.html#{esc(pub["id"])}">{keep_ids(esc(short_title(pub)))}</a>'
                            f'&nbsp;<span class="nowrap">({esc(venue_label(pub))})</span>.')
            links = p.get("links") or []
            if links:
                context = f'<span class="visually-hidden"> for {name}</span>'
                text.append('<span class="project__links">' + DOT.join(
                    f'<a href="{esc(link["url"])}">{esc(link["label"])}{context}</a>' for link in links) + "</span>")
            items.append(f'    <li id="{project_anchor(p)}">{" ".join(text)}</li>')
        sections.append(f"""<section class="projects" id="projects" aria-labelledby="projects-title">
  <h2 id="projects-title">Projects and artifacts</h2>{more}
  <ul class="project-list">
{chr(10).join(items)}
  </ul>
</section>""")
    rep_all = [ctx["pubs_by_id"][r] for t in themes for r in t.get("papers") or []]
    note = f'\n<p class="page-note">{bold_note(rep_all)}</p>' if rep_all else ""
    body = (f'{page_title("Research")}\n<div class="content content--research">\n'
            + "\n".join(sections) + f"{note}\n</div>")
    description = (f"Research directions of {site['name']} at {site['institution_short']}: "
                   + join_names([t["title"] for t in themes]) + ".")
    return render_page(ctx, "research", "Research", description, body)


# ---------------------------------------------------------------------------
# Publications
# ---------------------------------------------------------------------------

def page_publications(ctx):
    """The bibbase layout of comsec's Publications page: the introduction, then one collapsible gray bar
    per year ("2026 (11)", a <details> element open by default) above the year's citations. There is
    no filter; the Research page lists each direction's papers."""
    site = ctx["site"]
    data = ctx["publications"]
    pubs = data["publications"]
    lab = lab_names(ctx)
    profiles = data.get("profiles") or {}
    by_year = {}
    for p in pubs:
        by_year.setdefault(p["year"], []).append(p)
    years = sorted(by_year, reverse=True)
    profile_links = []
    if profiles.get("scholar"):
        profile_links.append(f'<a href="{esc(profiles["scholar"])}">Google Scholar</a>')
    if profiles.get("dblp"):
        profile_links.append(f'<a href="{esc(profiles["dblp"])}">DBLP</a>')
    since = data.get("since")
    scope = (f"This list covers {esc(site['name'])} publications since {since}, grouped by year."
             if since else f"This list covers {esc(site['name'])} publications, grouped by year.")
    profile_sentence = ""
    if profile_links:
        profile_sentence = (f" Earlier work and <span class=\"nowrap\">up-to-date</span> records are on the principal "
                            f"investigator’s {' and '.join(profile_links)} profiles.")
    sections = []
    for y in years:
        entries = "\n".join(pub_entry(ctx, p, lab, full=True) for p in by_year[y])
        sections.append(f"""<details class="year" id="y{y}" open>
<summary class="year__bar"><h2 class="year__h" id="y{y}-h">{y} <span class="year__count">({len(by_year[y])})</span></h2></summary>
<div class="year__body">
{entries}
</div>
</details>""")
    body = f"""{page_title("Publications")}
<div class="content content--pubs">
<p class="pub-intro">{scope} {bold_note(pubs)}{profile_sentence}</p>
<div class="pub-list">
{chr(10).join(sections)}
</div>
</div>"""
    description = (f"Publications of {site['name']} at {site['institution_short']}{since_text(ctx)}, "
                   "grouped by year.")
    return render_page(ctx, "publications", "Publications", description, body)


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

def person_name(name, url):
    name_html = f"<strong>{esc(name)}</strong>"
    return f'<a href="{esc(url)}">{name_html}</a>' if url else name_html


def page_people(ctx):
    """Plain lists, as in comsec's "Graduated doctoral students": the PI under the role heading (the
    name in bold, linked to the homepage, and the title), then each group in people.json and the
    alumni as bulleted lists. No photos, cards, avatars or bios. Every line is the name in bold, then
    the details after a comma, and alumni destinations after an arrow:
    "**Haoyan Xu**, co-advised with Prof. Yue Zhao", "**Vivan Doshi**, High school student -> an
    undergraduate at UC Berkeley"."""
    site = ctx["site"]
    people = ctx["people"]
    pi = people["pi"]
    parts = []
    pi_line = person_name(pi["name"], pi.get("url") or "")
    if pi.get("role"):
        pi_line += f', {esc(pi["title"])}'
    parts.append(f'<h2 id="pi-h">{esc(pi.get("role") or pi["title"])}</h2>\n<p class="pi">{pi_line}</p>')
    groups = [g for g in people.get("groups", []) if g.get("members")]
    for gi, g in enumerate(groups):
        # The heading already names the role when every member shares it.
        show_role = len({m["role"] for m in g["members"]}) > 1
        items = []
        for m in g["members"]:
            line = person_name(m["name"], m.get("url") or "")
            if show_role:
                line += f', {esc(m["role"])}'
            if m.get("note"):
                line += f', {inline(m["note"], "people.json.note")}'
            items.append(f"  <li>{line}</li>")
        parts.append(f'<h2 id="group-{gi + 1}-h">{esc(g["title"])}</h2>\n<ul class="people-list">\n'
                     + "\n".join(items) + "\n</ul>")
    alumni = people.get("alumni") or []
    if alumni:
        items = []
        for a in alumni:
            line = person_name(a["name"], a.get("url") or "") + f', {esc(a["role"])}'
            if a.get("years"):
                line += f', {esc(a["years"])}'
            if a.get("note"):
                line += f'; {inline(a["note"], "people.json.alumni.note")}'
            if a.get("now"):
                line += f' -&gt; {esc(a["now"])}'
            items.append(f"  <li>{line}</li>")
        parts.append('<h2 id="alumni-h">Alumni</h2>\n<ul class="people-list">\n' + "\n".join(items) + "\n</ul>")
    if groups:
        note = f'Interested in working with us? See how to <a href="join.html">{esc(keep_link("join " + site["name"]))}</a>.'
    else:
        note = (f'{esc(site["name"])} is growing. Prospective students can read how '
                f'to <a href="join.html">{esc(keep_link("join the lab"))}</a>.')
    parts.append(f'<p class="page-note">{note}</p>')
    body = f'{page_title("People")}\n<div class="content content--people">\n' + "\n".join(parts) + "\n</div>"
    description = f"The {site['name']} team at {site['institution_short']}: principal investigator, students, and alumni."
    return render_page(ctx, "people", "People", description, body)


# ---------------------------------------------------------------------------
# Teaching, news, join, contact, 404
# ---------------------------------------------------------------------------

def page_teaching(ctx):
    """The introduction, then one section per course: "CSCI 699: Title" (a link to the course page
    when there is one), the terms and status, and the description."""
    site = ctx["site"]
    data = ctx["teaching"]
    courses = data.get("courses") or []
    parts = []
    if data.get("intro"):
        parts.append(f'<p>{inline(data["intro"], "teaching.json.intro")}</p>')
    for i, c in enumerate(courses):
        hid = f"course-{i + 1}-h"
        terms = esc(", ".join(c["terms"])) if c["terms"] else ""
        status = f'<em class="status">{esc(c["status"])}</em>' if c.get("status") else ""
        line = DOT.join(x for x in (terms, status) if x)
        # As on comsec's Education page, the course name itself links to the course page.
        name = f'{esc(c["code"])}: {keep_ids(esc(c["title"]))}'
        if c.get("url"):
            name = f'<a href="{esc(c["url"])}">{name}</a>'
        rows = [f'  <h2 id="{hid}">{name}</h2>']
        if line:
            rows.append(f'  <p class="course__terms">{line}</p>')
        if c.get("description"):
            rows.append(f'  <p>{inline(c["description"], "teaching.json.description")}</p>')
        parts.append(f'<section class="course" aria-labelledby="{hid}">\n' + "\n".join(rows) + "\n</section>")
    if not courses:
        parts.append("<p>Course information will be added soon.</p>")
    body = f'{page_title("Teaching")}\n<div class="content content--teaching">\n' + "\n".join(parts) + "\n</div>"
    description = f"Graduate courses from {site['name']} at {site['institution_short']}."
    return render_page(ctx, "teaching", "Teaching", description, body)


def page_news(ctx):
    """Year headings, then the items: the date in bold and the headline, then the body. Each item keeps
    its anchor (news.html#2026-06-mc-oram-isca), which the sidebar links to."""
    site = ctx["site"]
    items = ctx["news"]["items"]
    by_year = {}
    for it in items:
        by_year.setdefault(it["_date"][0], []).append(it)
    sections = []
    for y in sorted(by_year, reverse=True):
        rows = []
        for it in by_year[y]:
            date = f'<time datetime="{iso_date(it["_date"])}">{esc(format_date(it["_date"]))}</time>'
            title = keep_ids(keep_venues(esc(curl(it["title"])), ctx))
            rows.append(f"""<article class="news-item" id="{esc(it['_id'])}">
  <h3 class="news-item__title"><span class="news-item__date">{date}</span><span class="news-item__sep" aria-hidden="true"> — </span><span class="visually-hidden">: </span>{title}</h3>
  <p>{inline(it["body"], "news.json " + it["_id"])}</p>
</article>""")
        sections.append(f'<section class="news-year" aria-labelledby="y{y}-h">\n<h2 id="y{y}-h">{y}</h2>\n'
                        + "\n".join(rows) + "\n</section>")
    content = "\n".join(sections) if sections else "<p>No news yet.</p>"
    body = f'{page_title("News")}\n<div class="content content--news">\n{content}\n</div>'
    description = f"News from {site['name']} at {site['institution_short']}: papers, talks, and lab updates."
    return render_page(ctx, "news", "News", description, body)


def mailto(email, subject=""):
    href = f"mailto:{email}"
    if subject:
        href += "?subject=" + quote(subject)
    return href


def page_join(ctx):
    """comsec's Join page: the introduction, then one h2 section per audience with its paragraphs. The
    last paragraph invites the reader to email the PI ("..., feel free to reach out to Prof. Li by
    email."), and the build ends it with the address, whose link pre-fills the audience's subject: "The
    address is mengyuanli@usc.edu; please use the subject “[SEPT PhD]”." So the request and the name
    are said once. The address is the link's text, so it can also be copied by a visitor without a mail
    program. An audience without body paragraphs gets the whole sentence instead: "Email Prof. Li at
    mengyuanli@usc.edu with the subject “[SEPT PhD]”." An audience's optional button label is not
    shown."""
    site = ctx["site"]
    data = ctx["join"]
    _, _, short = pi_names(ctx)
    email = ctx["people"]["pi"].get("email") or ""
    parts = [paragraphs(data.get("intro", []), "join.json.intro")] if data.get("intro") else []
    for aud in data.get("audiences", []):
        aid = esc(aud["id"])
        where = f"join.json.audiences.{aud['id']}"
        paras = [inline(p, f"{where}[{i}]") for i, p in enumerate(aud["body"])]
        if email:
            subject = aud.get("subject") or ""
            addr = f'<a href="{esc(mailto(email, subject))}">{esc(email)}</a>'
            subject_html = f'&nbsp;<span class="nowrap">“{esc(subject)}”</span>' if subject else ""
            if paras:
                paras[-1] += (f" The address is {addr}; please use the subject{subject_html}." if subject
                              else f" The address is {addr}.")
                if "mail" not in aud["body"][-1].lower():
                    WARNINGS.append(f"{where}: the build ends the last body paragraph with \"The address is "
                                    f"{email}\", so that paragraph should ask the reader to write by email, "
                                    f"as \"feel free to reach out to {short} by email.\" does")
            else:
                tail = f" with the subject{subject_html}" if subject else ""
                paras.append(f"Email {esc(tie(short))} at {addr}{tail}.")
        body = "\n".join(f"<p>{p}</p>" for p in paras)
        parts.append(f'<section class="audience" id="{aid}" aria-labelledby="{aid}-h">\n'
                     f'  <h2 id="{aid}-h">{esc(aud["title"])}</h2>\n{body}\n</section>')
    include = data.get("include")
    if include:
        items = "\n".join(f"  <li>{inline(i, 'join.json.include')}</li>" for i in include["items"])
        parts.append(f'<h2 id="include-h">{esc(include["title"])}</h2>\n<ul>\n{items}\n</ul>')
    if data.get("closing"):
        parts.append(f'<p class="page-note">{inline(data["closing"], "join.json.closing")}</p>')
    body = f'{page_title("Join")}\n<div class="content content--join">\n' + "\n".join(parts) + "\n</div>"
    description = f"How to join {site['name']} at {site['institution_short']}."
    return render_page(ctx, "join", "Join", description, body)


def page_contact(ctx):
    """The introduction, then Email, the department address with its source, the map links and the
    profile links, each under an h2."""
    site = ctx["site"]
    data = ctx["contact"]
    email = ctx["people"]["pi"].get("email") or ""
    parts = []
    if data.get("intro"):
        parts.append(f'<p>{inline(data["intro"], "contact.json.intro")}</p>')
    if email:
        parts.append(f'<h2 id="c-email">Email</h2>\n<p class="contact-email"><a href="{esc(mailto(email))}">{esc(email)}</a></p>')
    if data.get("address"):
        lines = "<br>".join(esc(line) for line in data["address"])
        source = ""
        if data.get("address_source"):
            s = data["address_source"]
            source = f'\n<p class="contact-source">Source: <a href="{esc(s["url"])}">{esc(s["label"])}</a></p>'
        parts.append(f'<h2 id="c-address">{esc(data.get("address_title") or "Address")}</h2>\n'
                     f'<address>{lines}</address>{source}')
    for hid, title, links in (("c-maps", "Maps and directions", data.get("maps")), ("c-links", "Online", data.get("links"))):
        if links:
            items = "\n".join(f'  <li><a href="{esc(m["url"])}">{esc(curl(m["label"]))}</a></li>' for m in links)
            parts.append(f'<h2 id="{hid}">{title}</h2>\n<ul>\n{items}\n</ul>')
    body = f'{page_title("Contact")}\n<div class="content content--contact">\n' + "\n".join(parts) + "\n</div>"
    description = f"How to contact {site['name']} at {site['institution_short']}."
    return render_page(ctx, "contact", "Contact", description, body)


def page_not_found(ctx):
    """404.html. GitHub Pages serves it for every missing path, including nested ones such as
    /news/2026/, where relative links would break, so its links become absolute once base_url is set."""
    site = ctx["site"]
    links = "\n".join(f'  <li><a href="{href}">{label}</a></li>' for href, label in
                      (("index.html", "Home"), ("research.html", "Research"), ("publications.html", "Publications"),
                       ("people.html", "People"), ("news.html", "News"), ("contact.html", "Contact")))
    body = (f'{page_title("Page not found")}\n<div class="content">\n'
            f'<p>This page does not exist or has moved.</p>\n<ul>\n{links}\n</ul>\n</div>')
    description = f"This page does not exist on the {site['name']} website."
    text = render_page(ctx, "not-found", "Page not found", description, body)
    base = esc((site.get("base_url") or "").rstrip("/"))
    if base:
        text = re.sub(r'(\s(?:href|src))="(?![a-zA-Z][a-zA-Z0-9+.-]*:|#)',
                      lambda m: f'{m.group(1)}="{base}/', text)
    return text


# ---------------------------------------------------------------------------
# Checks on the rendered pages
# ---------------------------------------------------------------------------

class IdCollector(HTMLParser):
    """Collects element ids, the attributes that refer to them, and link targets."""

    REF_ATTRS = ("aria-labelledby", "aria-describedby", "aria-controls", "for")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.refs = []
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is None:
                continue
            if name == "id":
                self.ids.append(value)
            elif name in self.REF_ATTRS:
                self.refs.extend((name, ref) for ref in value.split())
            elif name == "href":
                self.hrefs.append(value)


def check_rendered(pages):
    """Data ids become HTML ids, so a publication id such as 'main' could collide with the template.
    Links such as publications.html#crossline-ccs21 in text must point to an entry that is published."""
    collected = {}
    for name, text in pages.items():
        collector = IdCollector()
        collector.feed(text)
        collector.close()
        collected[name] = collector
    for name, collector in collected.items():
        seen = set()
        for element_id in collector.ids:
            if element_id in seen:
                ERRORS.add(f"rendered {name}", f"id {element_id!r} is used more than once; a publication, "
                           "theme, audience or news id probably collides with another id on the page")
            seen.add(element_id)
        for attr, ref in collector.refs:
            if ref not in seen:
                ERRORS.add(f"rendered {name}", f"{attr}={ref!r} refers to a missing id")
        for href in collector.hrefs:
            m = re.fullmatch(r"([^:/?#]*)#(.+)", href)  # a relative link to an anchor on a generated page
            target = m and (m.group(1) or name)
            if target in collected and m.group(2) not in collected[target].ids:
                ERRORS.add(f"rendered {name}", f"link {href!r} points to a missing anchor in {target}; "
                           "if it names a paper, check that the paper is published (publications.json 'since')")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_all():
    site = load_site()
    people = load_people()
    publications = load_publications()
    # Until ERRORS.raise_if_any() below, the data may hold wrong types, which load_*() have already
    # reported; the code up to there reads it defensively, so the build lists the problems instead
    # of stopping with a traceback.
    raw = publications.get("publications")
    all_pubs = [p for p in raw if isinstance(p, dict)] if isinstance(raw, list) else []
    pub_list = list(all_pubs)
    # Entries before "since" stay in the file but are not published; the rest of the
    # site may refer only to the papers that appear on the Publications page.
    since = publications.get("since")
    if isinstance(since, int) and not isinstance(since, bool):
        pub_list = [p for p in pub_list if not isinstance(p.get("year"), int) or p["year"] >= since]
    publications["publications"] = pub_list
    pubs_by_id = {p["id"]: p for p in pub_list if isinstance(p.get("id"), str)}
    research = load_research(set(pubs_by_id))
    ctx = {
        "site": site,
        "people": people,
        "publications": publications,
        "pubs_by_id": pubs_by_id,
        "news": load_news(),
        "research": research,
        "teaching": load_teaching(),
        "join": load_join(),
        "contact": load_contact(),
    }
    cross_check(ctx, all_pubs)
    load_graphics(ctx)
    ERRORS.raise_if_any()
    check_journey(ctx)
    # Newest first; keep the file order within a year.
    pub_list.sort(key=lambda p: p["year"], reverse=True)
    themes = research.get("themes") or []
    ctx["themes_by_id"] = {t["id"]: t for t in themes}
    # The papers tagged with each theme, newest first; untagged published papers count as "Other".
    ctx["theme_papers"] = {t["id"]: [p for p in pub_list if t["id"] in (p.get("themes") or [])] for t in themes}
    # Short venue names ("IEEE S&P", "NeurIPS"), longest first, each with an optional year after it;
    # keep_venues() uses them in news headlines.
    venues = sorted({esc(p["venue_short"]) for p in all_pubs if isinstance(p.get("venue_short"), str) and p["venue_short"]},
                    key=len, reverse=True)
    ctx["venue_re"] = (re.compile(r"(?<![\w&;/-])(?:" + "|".join(map(re.escape, venues)) + r")(?: \d{4})?(?![\w&/-])")
                       if venues else None)
    return ctx


def cross_check(ctx, all_pubs):
    """Checks that need more than one data file: theme ids on papers and projects, the papers a
    theme lists as representative, the home page's featured papers, and the journey's order of
    stops (site.json home.journey.order, every theme id of research.json once). It runs before the build
    stops for the problems found so far, so every value is type-checked before use (a wrong type
    has already been reported by load_*())."""
    def as_list(value):
        return value if isinstance(value, list) else []
    themes = [t for t in as_list(ctx["research"].get("themes")) if isinstance(t, dict)]
    theme_ids = {t.get("id") for t in themes if isinstance(t.get("id"), str)}
    for pub in all_pubs:
        for ref in as_list(pub.get("themes")):
            if isinstance(ref, str) and ref not in theme_ids:
                ERRORS.add(f"publications.json (id {pub.get('id')})",
                           f"unknown theme {ref!r} in themes; choose from {', '.join(sorted(theme_ids))}")
    pubs = ctx["pubs_by_id"]
    for theme in themes:
        for ref in as_list(theme.get("papers")):
            pub = pubs.get(ref) if isinstance(ref, str) else None
            if isinstance(pub, dict) and theme.get("id") not in as_list(pub.get("themes")):
                ERRORS.add(f"research.json (theme {theme.get('id')})",
                           f"representative paper {ref!r} is not tagged with this theme in publications.json "
                           f"(add {theme.get('id')!r} to its themes)")
    hw = "site.json.home.featured"
    home = ctx["site"].get("home")
    featured = as_list(home.get("featured")) if isinstance(home, dict) else []
    seen = set()
    for ref in featured:
        if not isinstance(ref, str):
            continue
        if ref in seen:
            ERRORS.add(hw, f"paper {ref!r} is listed twice")
        seen.add(ref)
        if ref not in pubs:
            ERRORS.add(hw, f"paper id {ref!r} is not a published entry in publications.json "
                       "(missing, or older than 'since')")
    # The journey's order: every theme of research.json once, in any order.
    journey = home.get("journey") if isinstance(home, dict) else None
    order = journey.get("order") if isinstance(journey, dict) else None
    if isinstance(order, list):
        jw = "site.json.home.journey.order"
        ids = [t["id"] for t in themes if isinstance(t.get("id"), str)]
        choices = ", ".join(ids) or "none defined"
        listed = set()
        for ref in order:
            if not isinstance(ref, str):
                continue  # load_site() has reported it
            if ref in listed:
                ERRORS.add(jw, f"theme {ref!r} is listed twice")
            elif ref not in theme_ids:
                ERRORS.add(jw, f"unknown theme {ref!r}; choose from {choices}")
            listed.add(ref)
        missing = [tid for tid in ids if tid not in listed]
        if missing:
            ERRORS.add(jw, f"leaves out {', '.join(repr(tid) for tid in missing)}; list each of research.json's "
                       f"{len(ids)} themes once ({choices}), or leave the field out for research.json's order")


def render_all(ctx):
    builders = {
        "home": page_home,
        "people": page_people,
        "research": page_research,
        "publications": page_publications,
        "teaching": page_teaching,
        "news": page_news,
        "join": page_join,
        "contact": page_contact,
    }
    pages = {PAGES[pid]: fn(ctx) for pid, fn in builders.items()}
    pages["404.html"] = page_not_found(ctx)  # not in PAGES, so it has no menu entry
    check_rendered(pages)
    ERRORS.raise_if_any()  # inline markup and ids are validated while rendering
    return pages


def is_build_output(path):
    """True for a top-level entry that a build writes: an HTML page, assets/, .nojekyll,
    or the .DS_Store that Finder adds."""
    if path.is_symlink():
        return False
    if path.name in (".nojekyll", ".DS_Store"):
        return path.is_file()
    if path.name == "assets":
        return path.is_dir()
    return path.suffix == ".html" and path.is_file()


def write(pages, out):
    """Replace the output directory with the pages, assets/ and .nojekyll.

    The directory is deleted first, so it must not be the project or hold its sources. An existing
    directory may hold only what a build writes, and if it holds anything besides Finder's .DS_Store
    it must carry the .nojekyll file that every build writes. A .nojekyll file alone proves nothing,
    because many GitHub Pages repositories have one at their root next to .git, CNAME and sources.
    """
    out = Path(out).expanduser().resolve()
    if out == ROOT or out in ROOT.parents or any(out == d or d in out.parents for d in (DATA, ASSETS)):
        sys.exit(f"build.py: refusing to write into {out}")
    if out.exists():
        if not out.is_dir():
            sys.exit(f"build.py: {out} is not a directory")
        entries = list(out.iterdir())
        stray = sorted(p.name for p in entries if not is_build_output(p))
        if stray:
            more = f" and {len(stray) - 5} more" if len(stray) > 5 else ""
            sys.exit(f"build.py: {out} contains files that build.py did not write "
                     f"({', '.join(stray[:5])}{more}); choose a new or empty directory")
        if any(p.name != ".DS_Store" for p in entries) and not (out / ".nojekyll").is_file():
            sys.exit(f"build.py: {out} is not empty and was not created by build.py; "
                     "choose a new or empty directory")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name, text in pages.items():
        (out / name).write_text(text, encoding="utf-8")
    shutil.copytree(ASSETS, out / "assets", ignore=shutil.ignore_patterns(*UNPUBLISHED_ASSETS))
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out


def main(argv):
    parser = argparse.ArgumentParser(prog="build.py",
                                     description="Build the SEPT Lab website from data/*.json.")
    parser.add_argument("--check", action="store_true",
                        help="validate data and render every page without writing files")
    parser.add_argument("--out", metavar="DIR", default=str(DIST),
                        help="output directory (default: dist/ next to build.py)")
    args = parser.parse_args(argv)
    ctx = load_all()
    pages = render_all(ctx)
    for warning in dict.fromkeys(WARNINGS):
        print(f"build.py: warning: {warning}", file=sys.stderr)
    if args.check:
        print(f"build.py: data files are valid and all {len(pages)} pages render.")
        return
    out = write(pages, args.out)
    shown = f"{out.relative_to(ROOT)}/" if ROOT in out.parents else f"{out}/"
    print(f"build.py: wrote {len(pages)} pages to {shown}")
    print(f"build.py: preview: {(out / 'index.html').as_uri()}")
    if not ctx["site"].get("base_url"):
        print("build.py: warning: site.json base_url is empty, so pages have no canonical URL and "
              "social previews have no image. Set it after the first deployment.", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
