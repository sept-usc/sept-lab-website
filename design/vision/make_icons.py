"""Generate the four SEPT research icons in the isometric line style of vision.svg.

Usage: python3 make_icons.py [out_dir]

Writes tee.svg, attacks.svg, verifiable-ai.svg and agent-security.svg (named by research.json theme
id). Every icon's viewBox is 250 units wide, so at the same display width their strokes render at the
same pixel width; at 150 px the 5-unit outlines are 3 px, close to the vision image's. The viewBox is
cropped to the drawing's height (plus PAD units above and below), so the drawing starts at the top of
its box and lines up with the direction's title on the Research page.
Colour rules follow the vision image: gold = protected, cardinal = the trust path (or, on the
vulnerabilities icon, the flaw).
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from iso import Scene, INK, GOLD, RED, WHITE, R2
import parts

MAJ, MIN, TH = 5.0, 3.0, 7.5
M = 250      # viewBox width, shared by all icons
PAD = 6      # space above and below the drawing, enough for the outline's half width
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE


def new():
    return Scene(sw=MAJ, swd=MIN)


def save(s, name, title):
    p = os.path.join(OUT, name)
    x, y, w, h = s.bbox(0)
    assert w <= M - 8 and h <= M - 8, (name, w, h)
    cx = x + w / 2
    open(p, "w").write(s.svg(title, vb=(cx - M / 2, y - PAD, M, h + 2 * PAD), decorative=True))
    print(p, [round(v) for v in (w, h)])


def tee():
    """a chip with bold pads; a gold enclave on its die holds the cardinal root of trust"""
    s = new()
    parts.chip(s, 0, 0, 120, 18, n=4, pitch=25, pin=(11, 15, 7), inset=15, pin_sw=MIN)
    s.cbox(0, 0, 18, 54, 54, 26, top=GOLD, left=GOLD)
    s.disc(0, 0, 44, 9, fill=RED, stroke=None)
    save(s, "tee.svg", "TEEs and Confidential Computing")


def crack_poly(center, widths, axis):
    left, right = [], []
    for (u, v), w in zip(center, widths):
        left.append(axis(u - w, v)); right.append(axis(u + w, v))
    return left + right[::-1]


def attacks():
    """the system box of the vision image (with its window bar), split by a cardinal crack"""
    s = new()
    a, h = 108, 84
    s.cbox(0, 0, 0, a, a, h)
    y1 = a / 2
    parts.window_bar(s, 0, y1, h, a, MIN, 5.5, inset=16, dots=(11, 21))
    top_c = [(10, -a / 2), (-6, -30), (12, -8), (-8, 16), (6, 38), (-2, a / 2)]
    top_w = [0, 3, 4, 5, 6, 7]
    s.poly(crack_poly(top_c, top_w, lambda u, v: (u, v, h)), fill=RED, stroke=RED, sw=2)
    fr = [(-2, h), (-2, h - 16), (10, h - 34), (-6, h - 52), (6, h - 70)]
    fw = [7, 7, 5, 3, 0]
    s.poly(crack_poly(fr, fw, lambda u, v: (u, y1, v)), fill=RED, stroke=RED, sw=2)
    save(s, "attacks.svg", "System and Hardware Vulnerabilities")


def verifiable():
    """a five-node network on a plate; a short cardinal path ends in a gold output with a check"""
    s = new()
    s.cbox(0, 0, -16, 140, 128, 16)
    inp = [(-42, 40), (42, 40)]
    hid = [(-42, 0), (42, 0)]
    out = (0, -36)
    path = [(42, 64), inp[1], hid[0], out]
    for p in inp:
        for q in hid:
            if (p, q) != (inp[1], hid[0]):
                s.line([(p[0], p[1], 0), (q[0], q[1], 0)], sw=MIN)
    s.line([(hid[1][0], hid[1][1], 0), (out[0], out[1], 0)], sw=MIN)
    s.line([(x, y, 0) for x, y in path], stroke=RED, sw=TH)
    r, h = 22, 26
    sx, sy0, sy1, rx = s.cyl(out[0], out[1], 0, r, h, top=GOLD, side=GOLD)
    parts.check_on_cyl(s, sx, sy1, R2 * 0.5 * r, h, 22, 4.5)
    for x, y in sorted(hid + inp, key=lambda q: q[0] + q[1]):
        s.cyl(x, y, 0, 13, 10, sw=4.5)
    save(s, "verifiable-ai.svg", "Verifiable AI")


def agent():
    """the gold agent block with the AI spark, and the tool it uses isolated in a cage"""
    s = new()
    a = 70
    ax, ay = -34, 8
    cx, cy, c = 62, -42, 60          # behind and right of the block: they never overlap on screen
    parts.cage(s, cx, cy, c, False, sw=MIN)
    parts.gear(s, cx, cy, 0, 24, 12, teeth=8, sw=4, hole_sw=MIN)
    parts.cage(s, cx, cy, c, True, sw=MIN)
    s.line([(ax + a / 2 + 5, -20, 0), (cx - c / 2 - 5, -20, 0)], dash="0.1 10", sw=6)
    s.cbox(ax, ay, 0, a, a, a, top=GOLD, left=GOLD)
    parts.spark(s, ax + 2, ay + a / 2, a * 0.5, 23)
    save(s, "agent-security.svg", "AI Agent Security")


os.makedirs(OUT, exist_ok=True)
tee(); attacks(); verifiable(); agent()
