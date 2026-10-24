#!/usr/bin/env python3
"""Check the generated site in dist/.

- Every relative href/src points to an existing file inside dist/ and, for links
  with a #fragment, to an existing id in the target page. So does every data-*-href
  and data-*-src attribute, which scripts follow (the journey's files on the home
  page's link, the Research and Publications pages on its dialog).
- No page uses the same id twice.
- Every aria-labelledby, aria-describedby, aria-controls and label `for`
  value refers to an id on the same page.

Usage: python3 tools/check_links.py [DIST]
DIST defaults to dist/ in the project; pass the directory given to build.py --out
to check a build elsewhere. External links (http, https, mailto) are counted but
not fetched.
"""

import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ID_REF_ATTRS = ("aria-labelledby", "aria-describedby", "aria-controls", "for")


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []      # (tag, attribute, value, line)
        self.ids = set()
        self.duplicates = []  # (id, line)
        self.id_refs = []   # (attribute, id, line)

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for name, value in attrs:
            if value is None:
                continue
            if name == "id":
                if value in self.ids:
                    self.duplicates.append((value, line))
                self.ids.add(value)
            elif name in ("href", "src") or (name.startswith("data-") and name.endswith(("-href", "-src"))):
                self.refs.append((tag, name, value, line))
            elif name in ID_REF_ATTRS:
                self.id_refs.extend((name, ref, line) for ref in value.split())


def parse(path):
    collector = Collector()
    collector.feed(path.read_text(encoding="utf-8"))
    collector.close()
    return collector


DEFAULT_DIST = Path(__file__).resolve().parent.parent / "dist"


def main(argv):
    parser = argparse.ArgumentParser(prog="check_links.py",
                                     description="Check relative links, #anchors and id references "
                                                 "in a site built by build.py.")
    parser.add_argument("dist", nargs="?", default=str(DEFAULT_DIST),
                        help="directory with the built site (default: dist/ in the project)")
    dist = Path(parser.parse_args(argv).dist).expanduser().resolve()
    pages = sorted(dist.glob("*.html"))
    if not pages:
        sys.exit(f"check_links: no HTML files in {dist}; run python3 build.py first")
    parsed = {p.resolve(): parse(p) for p in pages}
    problems, external = [], set()
    checked = 0
    for page, data in parsed.items():
        for value, line in data.duplicates:
            problems.append(f"{page.name}:{line}: id {value!r} is used more than once")
        for attr, ref, line in data.id_refs:
            if ref not in data.ids:
                problems.append(f"{page.name}:{line}: {attr}={ref!r} refers to a missing id")
        for tag, attr, value, line in data.refs:
            parts = urlsplit(value)
            if parts.scheme in ("http", "https", "mailto"):
                external.add(value)
                continue
            if parts.scheme or value.startswith("//"):
                problems.append(f"{page.name}:{line}: unexpected scheme in {value!r}")
                continue
            if value.startswith("/"):
                problems.append(f"{page.name}:{line}: root-relative link {value!r} breaks under a subpath")
                continue
            checked += 1
            target = (page.parent / unquote(parts.path)).resolve() if parts.path else page
            if not target.is_relative_to(dist):
                problems.append(f"{page.name}:{line}: {value!r} points outside dist/ and will break once deployed")
                continue
            if not target.is_file():
                problems.append(f"{page.name}:{line}: <{tag} {attr}> {value!r} -> missing file")
                continue
            if parts.fragment:
                if target.suffix != ".html":
                    continue
                ids = parsed[target].ids if target in parsed else parse(target).ids
                if unquote(parts.fragment) not in ids:
                    problems.append(f"{page.name}:{line}: {value!r} -> no element with id "
                                    f"{parts.fragment!r} in {target.name}")
    print(f"check_links: {len(pages)} pages, {checked} relative links checked, "
          f"{len(external)} distinct external links not fetched.")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("check_links: all relative links resolve; ids are unique and every id reference resolves.")


if __name__ == "__main__":
    main(sys.argv[1:])
