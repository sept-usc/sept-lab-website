#!/usr/bin/env python3
"""Notify IndexNow of canonical HTML changes after deployment (stdlib only).

The public key in indexnow.json is served as /<key>.txt; it is not a secret.
State records received notifications, not indexing. A missing state bootstraps the
current sitemap. --dry-run validates and prints a deterministic plan without
network requests or state writes. See https://www.indexnow.org/documentation.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

ENDPOINT = "https://api.indexnow.org/indexnow"
VERSION = 1
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SEMANTIC_ATTRS = {"alt", "datetime", "href", "lang", "src", "title", "aria-label"}
META_NAMES = {"description", "robots", "googlebot", "bingbot", "author"}


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("IndexNow config must be a JSON object")
    host, key = config.get("host", ""), config.get("key", "")
    if not isinstance(host, str) or not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)+", host):
        raise ValueError("IndexNow host must be a lowercase DNS hostname without a scheme or path")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9-]{8,128}", key):
        raise ValueError("IndexNow key must contain 8–128 ASCII letters, digits or dashes")
    return {"host": host, "key": key}


def own_url(url, host):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != host or not parts.path.startswith("/")
            or parts.query or parts.fragment or re.search(r"[\s\\]", url)):
        raise ValueError(f"not a canonical HTTPS URL on {host}: {url}")
    decoded = unquote(parts.path)
    if any(part in (".", "..") for part in decoded.split("/")) or "%" in decoded or "\\" in decoded:
        raise ValueError(f"unsafe encoded URL path: {url}")
    return parts.path


class Page(HTMLParser):
    """Fingerprint search metadata and main content, excluding scripts/site chrome.

    A global build digest, analytics configuration, footer year, navigation or
    sidebar update should not resubmit every article. Visible main text, links,
    images, title, descriptions, alternates and structured data remain covered.
    """
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.stack, self.main, self.title, self.ld = [], [], [], []
        self.meta, self.links, self.canonicals = [], [], []
        self.noindex, self.has_main = False, False
        self._title, self._ld = False, None
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title" and any(item[0] == "head" for item in self.stack):
            self._title = True
        if tag == "link":
            rel = (attrs.get("rel") or "").lower().split()
            if "canonical" in rel:
                self.canonicals.append(attrs.get("href"))
            if set(rel) & {"canonical", "alternate"}:
                self.links.append(sorted((k, v) for k, v in attrs.items() if k in {"rel", "href", "hreflang", "type"}))
        if tag == "meta":
            name = (attrs.get("name") or attrs.get("property") or "").lower()
            value = attrs.get("content") or ""
            if name in {"robots", "googlebot", "bingbot"} and set(re.split(r"[,\s]+", value.lower())) & {"noindex", "none"}:
                self.noindex = True
            if name in META_NAMES or name.startswith(("og:", "twitter:")):
                self.meta.append((name, value))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._ld = []
        parent_main = bool(self.stack and self.stack[-1][1])
        parent_blocked = bool(self.stack and self.stack[-1][2])
        in_main = parent_main or tag == "main"
        if tag == "main":
            self.has_main = True
        classes = set((attrs.get("class") or "").split())
        blocked = (parent_blocked or tag in {"script", "style", "nav", "footer"}
                   or "hidden" in attrs or attrs.get("aria-hidden") == "true"
                   or bool(classes & {"doc-aside", "sidebar", "chat-aside"}))
        if in_main and not blocked:
            self.main.append((tag, sorted((k, v) for k, v in attrs.items() if k in SEMANTIC_ATTRS)))
        if tag not in VOID:
            self.stack.append((tag, in_main, blocked))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False
        if tag == "script" and self._ld is not None:
            self.ld.append(json.loads("".join(self._ld)))
            self._ld = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
        if self._title:
            self.title.append(data)
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:
            text = " ".join(data.split())
            if text:
                self.main.append(text)

    def fingerprint(self):
        if not self.has_main:
            raise ValueError("indexable page has no <main>; refusing an incomplete fingerprint")
        data = {"title": " ".join("".join(self.title).split()), "meta": sorted(self.meta),
                "links": sorted(self.links), "structured_data": self.ld, "main": self.main}
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def snapshot(site_dir, config):
    site_dir = Path(site_dir).resolve()
    key_path = site_dir / (config["key"] + ".txt")
    if key_path.read_text(encoding="utf-8").strip() != config["key"]:
        raise ValueError("built IndexNow key file does not match indexnow.json")
    tree = ET.parse(site_dir / "sitemap.xml")
    if tree.getroot().tag.rsplit("}", 1)[-1] != "urlset":
        raise ValueError("expected a sitemap urlset, not a sitemap index")
    robots = RobotFileParser()
    robots.parse((site_dir / "robots.txt").read_text(encoding="utf-8").splitlines())
    pages = {}
    for item in tree.getroot():
        locs = [el.text for el in item if el.tag.rsplit("}", 1)[-1] == "loc"]
        if len(locs) != 1 or not locs[0]:
            raise ValueError("each sitemap entry needs one loc")
        url = locs[0]
        path = own_url(url, config["host"])
        target = (site_dir / unquote(path).lstrip("/"))
        if path.endswith("/"):
            target = target / "index.html"
        if site_dir not in target.resolve().parents:
            raise ValueError(f"page escapes build directory: {url}")
        if target.suffix != ".html":
            raise ValueError(f"sitemap entry is not an HTML page: {url}")
        page = Page(target.read_text(encoding="utf-8"))
        if (page.noindex or page.canonicals != [url]
                or any(not robots.can_fetch(agent, url) for agent in ("*", "bingbot"))):
            continue
        if url in pages:
            raise ValueError(f"duplicate sitemap URL: {url}")
        pages[url] = page.fingerprint()
    if not pages:
        raise ValueError("no canonical indexable HTML pages found; refusing a mass deletion")
    return dict(sorted(pages.items()))


def read_state(path, host):
    path = Path(path)
    if not path.exists():
        return {}
    state = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(state, dict) or state.get("version") != VERSION
            or state.get("host") != host or not isinstance(state.get("pages"), dict)):
        raise ValueError("IndexNow state has the wrong host, version or pages format")
    for url, digest in state["pages"].items():
        own_url(url, host)
        if not isinstance(digest, str) or not re.fullmatch("[a-f0-9]{64}", digest):
            raise ValueError(f"invalid stored fingerprint for {url}")
    return state["pages"]


def plan(current, previous):
    return {"added": sorted(set(current) - set(previous)),
            "changed": sorted(url for url in current.keys() & previous.keys() if current[url] != previous[url]),
            "deleted": sorted(set(previous) - set(current))}


def verify_live_key(config, attempts=6, delay=10):
    url = f"https://{config['host']}/{config['key']}.txt"
    error = "not checked"
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "IndexNow-site-notifier/1.0", "Cache-Control": "no-cache"})
            with urlopen(request, timeout=30) as response:
                if response.status == 200 and response.geturl() == url and response.read(2048).decode("utf-8").strip() == config["key"]:
                    return
                error = "key URL did not return HTTP 200 with the expected key at its canonical URL"
        except HTTPError as exc:
            error = str(exc)
            exc.close()
        except (URLError, TimeoutError, OSError, UnicodeError) as exc:
            error = str(exc)
        if attempt + 1 < attempts:
            time.sleep(delay)
    raise ValueError(f"deployed key is not ready after {attempts} attempt(s): {error}")


def submit(config, urls):
    payload = {"host": config["host"], "key": config["key"],
               "keyLocation": f"https://{config['host']}/{config['key']}.txt", "urlList": urls}
    request = Request(ENDPOINT, data=json.dumps(payload, separators=(",", ":")).encode(),
                      headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "IndexNow-site-notifier/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            status = response.status
    except HTTPError as exc:
        headers = exc.headers or {}
        extra = f"; Retry-After: {headers.get('Retry-After')}" if headers.get("Retry-After") else ""
        reasons = {400: "invalid request format", 403: "key validation failed", 422: "host/key/URL mismatch", 429: "rate limited; retry later"}
        exc.close()
        raise ValueError(f"IndexNow HTTP {exc.code}: {reasons.get(exc.code, 'notification failed')}{extra}") from exc
    if status not in (200, 202):
        raise ValueError(f"unexpected IndexNow HTTP {status}; state was not advanced")
    return status


def write_state(path, host, pages):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps({"version": VERSION, "host": host, "pages": pages}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("indexnow.json"))
    parser.add_argument("--state", type=Path, default=Path(".indexnow-state.json"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--key-attempts", type=int, default=6)
    parser.add_argument("--key-delay", type=float, default=10)
    args = parser.parse_args(argv)
    if args.key_attempts < 1 or args.key_delay < 0:
        parser.error("--key-attempts must be positive and --key-delay nonnegative")
    try:
        config = load_config(args.config)
        current = snapshot(args.site_dir, config)
        previous = read_state(args.state, config["host"])
        changes = plan(current, previous)
        print(json.dumps({"dry_run": args.dry_run, "host": config["host"], **changes}, sort_keys=True))
        urls = sorted(set(sum(changes.values(), [])))
        if args.dry_run or not urls:
            print("Dry run; no requests or state changes." if args.dry_run else "No indexable content changes; no notification sent.")
            return 0
        verify_live_key(config, args.key_attempts, args.key_delay)
        received = dict(previous)
        for offset in range(0, len(urls), 10000):
            batch = urls[offset:offset + 10000]
            status = submit(config, batch)
            for url in batch:
                if url in current:
                    received[url] = current[url]
                else:
                    received.pop(url, None)
            # Preserve successful batches if a later batch fails; failed URLs retry on the next run.
            write_state(args.state, config["host"], received)
            detail = "received; key validation pending" if status == 202 else "received"
            print(f"IndexNow HTTP {status}: {len(batch)} URL(s) {detail}. Crawling and indexing are not guaranteed.")
        return 0
    except (ValueError, OSError, URLError, ET.ParseError) as exc:
        print(f"IndexNow notification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
