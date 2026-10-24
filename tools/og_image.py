#!/usr/bin/env python3
"""Write the page from which the social-preview image, assets/img/og-image.jpg, is rendered.

The image is the site's masthead on white, in Karla: the logo mark, the name ("SEPT" in
cardinal, "Lab" in ink), a thin vertical rule and the affiliation on two lines, and under them the
site title ("Security, Privacy, and Trust Lab") in gray, above a thin cardinal rule at the bottom
edge. This script builds that 1200 by 630 px page from data/site.json (wordmark, expansion,
lockup.affiliation), design/sept-mark.png and the colors on :root in assets/css/style.css, so the
picture follows the data. Render it again whenever the name, the tagline, the mark or those colors
change, and update site.json og_image.alt if the picture changes.

Usage:
    python3 tools/og_image.py                 # write the page and print how to render it
    python3 tools/og_image.py --out FILE      # write the page to FILE instead
    python3 tools/og_image.py --render        # also screenshot it into design/og-image.png with
                                              # headless Chrome and convert that into
                                              # assets/img/og-image.jpg with sips (macOS)

Set CHROME to the browser's executable if it is not in the usual place. Requires Python 3.9 or
later and nothing outside the standard library.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "data" / "site.json"
CSS = ROOT / "assets" / "css" / "style.css"
MARK = ROOT / "design" / "sept-mark.png"
PNG = ROOT / "design" / "og-image.png"
JPG = ROOT / "assets" / "img" / "og-image.jpg"
WIDTH, HEIGHT = 1200, 630
CHROME_PATHS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium",
                "chromium-browser")
# The site's family, as build.py loads it.
FONTS = "https://fonts.googleapis.com/css2?family=Karla:wght@700&amp;display=swap"
# The stylesheet's tokens used in the picture, with their values at the time of writing as fallbacks.
TOKENS = {"paper": "#ffffff", "ink": "#1f1f1f", "title": "#464646", "accent": "#990000", "nav-rule": "#edeeee"}


def esc(text):
    return html.escape(str(text), quote=True)


def tokens():
    """The colors from :root in assets/css/style.css, so the image follows the palette."""
    css = CSS.read_text(encoding="utf-8")
    found = dict(TOKENS)
    for name in TOKENS:
        m = re.search(r"--%s:\s*(#[0-9a-fA-F]{3,8})\s*;" % re.escape(name), css)
        if m:
            found[name] = m.group(1)
    return found


def page():
    site = json.loads(SITE.read_text(encoding="utf-8"))
    c = tokens()
    word = site["wordmark"]
    rest = f" {esc(word['rest'])}" if word.get("rest") else ""
    # The affiliation on two lines of similar length and the site title, as build.py sets them.
    words = (site["lockup"].get("affiliation") or "").split()
    cut = min(range(1, len(words)), key=lambda i: max(len(" ".join(words[:i])), len(" ".join(words[i:])))) \
        if len(words) > 1 else len(words)
    aff = "".join(f"<span>{esc(' '.join(part))}</span>" for part in (words[:cut], words[cut:]) if part)
    aff_html = f'<i class="rule"></i><p class="aff">{aff}</p>' if aff else ""
    expansion = site.get("expansion") or ""
    title = f"{expansion} {word.get('rest') or ''}".strip() if expansion else site["name"]
    # The 200 by 240 px master of the mark, sharper than the header's copy at the picture's size.
    mark = (MARK if MARK.is_file() else ROOT / site["lockup"]["mark"]).as_uri()
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{FONTS}">
<style>
html,body{{margin:0;width:{WIDTH}px;height:{HEIGHT}px;overflow:hidden;background:{c['paper']}}}
.card{{box-sizing:border-box;width:{WIDTH}px;height:{HEIGHT}px;display:flex;flex-direction:column;
align-items:center;justify-content:center;border-bottom:6px solid {c['accent']};
font-family:"Karla","Helvetica Neue",Arial,sans-serif;font-weight:700;color:{c['ink']}}}
.lockup{{display:flex;align-items:center}}
.lockup img{{height:150px;width:auto;flex:none}}
.name{{margin:0 0 0 24px;font-size:100px;line-height:1;letter-spacing:-2.5px;white-space:nowrap}}
.name span{{color:{c['accent']}}}
.rule{{align-self:stretch;width:3px;margin:0 40px;background:{c['ink']}}}
.aff{{margin:0;font-size:35px;line-height:1.2;letter-spacing:-.5px}}
.aff span{{display:block;white-space:nowrap}}
.title{{margin:58px 0 0;padding-top:48px;border-top:2px solid {c['nav-rule']};width:1000px;text-align:center;
font-size:58px;line-height:1.2;letter-spacing:-1.5px;color:{c['title']}}}
</style></head><body><div class="card">
<div class="lockup"><img src="{esc(mark)}" alt=""><p class="name"><span>{esc(word['accent'])}</span>{rest}</p>{aff_html}</div>
<p class="title">{esc(title)}</p></div></body></html>
"""


def chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for candidate in CHROME_PATHS:
        if os.path.isfile(candidate) or shutil.which(candidate):
            return shutil.which(candidate) or candidate
    return None


def render(out):
    browser = chrome()
    if not browser:
        sys.exit("og_image.py: no Chrome found; set CHROME to the browser's executable.")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--virtual-time-budget=5000", f"--window-size={WIDTH},{HEIGHT}", f"--screenshot={PNG}",
                    out.as_uri()], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"og_image.py: wrote {PNG.relative_to(ROOT)}")
    if not shutil.which("sips"):
        sys.exit("og_image.py: sips (macOS) is not available; convert design/og-image.png into "
                 "assets/img/og-image.jpg at JPEG quality 82 with another tool.")
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", str(PNG), "--out", str(JPG)],
                   check=True, stdout=subprocess.DEVNULL)
    print(f"og_image.py: wrote {JPG.relative_to(ROOT)}")


def main(argv):
    parser = argparse.ArgumentParser(prog="og_image.py",
                                     description="Write the page that the social-preview image is rendered from.")
    parser.add_argument("--out", metavar="FILE", default=str(Path(tempfile.gettempdir()) / "sept-og-image.html"),
                        help="where to write the page (default: sept-og-image.html in the temporary directory)")
    parser.add_argument("--render", action="store_true",
                        help="also render design/og-image.png with headless Chrome and assets/img/og-image.jpg with sips")
    args = parser.parse_args(argv)
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(), encoding="utf-8")
    print(f"og_image.py: wrote {out}")
    if args.render:
        render(out)
    else:
        print("og_image.py: render it with python3 tools/og_image.py --render, or by hand: headless Chrome at "
              f"{WIDTH}x{HEIGHT} (--screenshot=design/og-image.png), then sips -s format jpeg -s formatOptions 82 "
              "design/og-image.png --out assets/img/og-image.jpg")


if __name__ == "__main__":
    main(sys.argv[1:])
