"""Generate vision.svg, the SEPT Lab vision image: a trust stack in four isometric layers.

Usage: python3 make_vision.py [out.svg] [--check] [--motion]

Reading from bottom to top: I Hardware (a chip whose gold enclave holds a cardinal root of trust),
II Systems (three VMs on a hypervisor, the middle one gold: confidential; a cardinal crack splits the
right one, as on the vulnerabilities icon: the lab's first thrust), III Models (a small
network; the inference path is cardinal and ends in a gold output node with a check: verified),
IV Agents (a gold agent block with the AI spark, using a tool isolated in a wireframe cage).
Gold marks what is protected on each layer; one cardinal thread, the chain of trust, rises from the
root of trust through each gold element to the agent. The four labels are research.json theme
`layer` values (the build warns when one is missing from the drawing).

Layers are painted bottom to top, so an upper slab correctly covers the hidden part of the riser
below it. --check prints, per layer, how far the lower layer's objects stay clear of the slab above
(negative = occluded).

Motion hooks. The home page animates the drawing with keyframes in the site's stylesheet
(assets/css/style.css, "Vision image: motion"), which target the classes below once the build has
prefixed them (sv-pu1 becomes vision-sv-pu1). The hooks change nothing in the still drawing:
  sv-ly, sv-l0..sv-l3  one group per layer (slab, objects, and the riser up to the next layer); the
                       layer's label has its sv-l class too
  sv-th                the pieces of the cardinal thread, in the order of the chain
  sv-pu, sv-pu1..6     a pulse overlay right after each piece: the same path with no stroke, so it is
                       covered exactly like the thread; the stylesheet gives it a stroke and moves a
                       dash along it
  sv-rt, sv-vi1..3     the root of trust and the via where the thread comes up through each layer
  sv-gd, sv-gd0..3     the gold faces of each layer's protected element
  sv-nd1, sv-nd2       the two network nodes on the inference path (sv-nd)
  sv-ck                the check mark on the gold output node
  sv-cr                the two shapes of the crack
  sv-ln                the dotted link from the agent to its tool
  sv-sp, sv-sp0..2     the AI spark as drawn (sv-sp0) and two hidden frames of it with the stars
                       grown (SPARK_FRAMES), for its twinkle
  sv-gr, sv-gr0..3     the gear as drawn (sv-gr0) and three hidden frames of it turned by a quarter,
                       half and three quarters of a tooth, which the stylesheet shows in turn
Moving parts change paint properties only (fill, stroke, the dash, visibility): opacity and transform
would let the browser composite them, which renders the drawing's edges differently from the still
image. The one exception is the short intro, which moves the layer groups.
--motion prints the animation delays for the stylesheet, computed from the lengths of the thread
pieces so that the pulse moves at one speed through the whole chain (see TIMING below).
"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from iso import Scene, INK, GOLD, RED, WHITE, C, R2, f
import parts

# ---------------------------------------------------------------- geometry
LX, LY = 244, 140       # slab plan size
T, T0 = 16, 26          # slab thickness; the hardware slab is the heavier foundation
D, H = 70, 100          # each layer steps back D (-Y) and up H
MAJ, MIN, TH = 3.0, 1.6, 5.5   # outline, detail and thread weights
DOT = 3.2               # dotted links and window-bar dots
VIA_R = 6.0
GEAR_FRAMES = 3         # hidden frames of the gear between two teeth
SPARK_FRAMES = [(1.12, 1.8), (1.05, 1.35)]   # hidden frames of the spark: big and small star grown

s = Scene(sw=MAJ, swd=MIN, wcls={MAJ: "sv-o", MIN: "sv-d", TH: "sv-t", DOT: "sv-p"})
EXIT = {}               # layer -> (x, y, z): where its riser leaves the top of its gold element
KEEP = {i: [] for i in range(4)}   # object points that must stay visible (for --check)
CHAIN = []              # the thread pieces in the order of the chain, as screen polylines
STOPS = {}              # distances along a piece where the pulse passes something (for --motion)


def at(i):
    s.off = (0, -i * D, i * H)


def slab(i):
    at(i)
    t = T0 if i == 0 else T
    s.box(-LX / 2, -LY / 2, -t, LX, LY, t)


def via(i):
    """the dot where the riser from layer i-1 comes up through layer i"""
    x, y, _ = EXIT[i - 1]
    s.disc(x, y + D, 0, VIA_R, fill=RED, stroke=None, cls=f"sv-vi sv-vi{i}")
    return x, y + D


def thread(pts, cap="round"):
    """A piece of the chain of trust, followed at once by its pulse overlay: the same path without a
    stroke, so that everything painted later covers the pulse exactly where it covers the thread."""
    s.line(pts, stroke=RED, sw=TH, cap=cap, cls="sv-th")
    pts2 = [s.P(*p, track=False) for p in pts]
    k = len(CHAIN) + 1
    d = "M" + " L".join(f"{f(a)},{f(b)}" for a, b in pts2)
    s.raw(f'<path d="{d}" fill="none" stroke="none" class="sv-pu sv-pu{k}"/>')
    CHAIN.append(pts2)


def riser(i):
    """from the top of layer i's gold element straight up to the top face of layer i+1; the slab of
    layer i+1, painted next, hides the part inside and behind it"""
    at(i)
    x, y, z = EXIT[i]
    thread([(x, y, z), (x, y, H)], cap="butt")


def keep(i, pts):
    for p in pts:
        KEEP[i].append(s.P(*p, track=False))


# ---------------------------------------------------------------- layer art
def hardware():
    at(0)
    cx, cy, w, ch = 0, -12, 88, 13
    n, p = 6, 12
    ks = [(k - (n - 1) / 2) * p for k in range(n)]
    # traces with via pads: front pins to the front edge, right pins to the right edge
    for k in ks:
        s.line([(cx + k, cy + w / 2 + 6, 0), (cx + k, LY / 2 - 11, 0)])
        s.disc(cx + k, LY / 2 - 11, 0, 2.8, fill=INK, stroke=None)
        s.line([(cx + w / 2 + 6, cy + k, 0), (LX / 2 - 16, cy + k, 0)])
        s.disc(LX / 2 - 16, cy + k, 0, 2.8, fill=INK, stroke=None)
    parts.chip(s, cx, cy, w, ch, n=n, pitch=p, pin=(4, 8, 3), inset=13, pin_sw=MIN)
    e, eh = 38, 9
    s.cbox(cx, cy, ch, e, e, eh, top=GOLD, left=GOLD, cls="sv-gd sv-gd0")
    s.disc(cx, cy, ch + eh, 7.5, fill=RED, stroke=None, cls="sv-rt")          # root of trust
    EXIT[0] = (cx, cy, ch + eh)
    keep(0, [(cx - e / 2, cy - e / 2, ch + eh), (cx + e / 2, cy - e / 2, ch + eh),
             (cx - w / 2 - 8, cy - w / 2, 3), (cx + w / 2, cy - w / 2 - 8, 3)])


def crack(x, cy, vm, z_top, scale=0.5):
    """The cardinal crack of the vulnerabilities icon (make_icons.attacks), scaled to a VM of side vm:
    across the top face from back to front, then down the front (+Y) face."""
    def poly(center, widths, axis):
        left = [axis(u - w, v) for (u, v), w in zip(center, widths)]
        right = [axis(u + w, v) for (u, v), w in zip(center, widths)]
        return left + right[::-1]
    k = scale
    top_c = [(10 * k, -vm / 2), (-6 * k, -30 * k), (12 * k, -8 * k), (-8 * k, 16 * k), (6 * k, 38 * k),
             (-2 * k, vm / 2)]
    top_w = [0, 1.6, 2.2, 2.8, 3.3, 3.8]
    s.poly(poly(top_c, top_w, lambda u, v: (x + u, cy + v, z_top)), fill=RED, stroke=RED, sw=1, cls="sv-cr")
    y1 = cy + vm / 2
    fr = [(-2 * k, z_top), (-2 * k, z_top - 6), (10 * k, z_top - 13), (-6 * k, z_top - 20), (6 * k, z_top - 27)]
    fw = [3.8, 3.8, 2.8, 1.6, 0]
    s.poly(poly(fr, fw, lambda u, v: (x + u, y1, v)), fill=RED, stroke=RED, sw=1, cls="sv-cr")


def systems():
    at(1)
    vx, vy = via(1)
    vm, vh, ph, pd, pw = 54, 32, 8, 86, 212
    cy = -7
    py = cy + pd / 2                                   # plate front edge
    s.cbox(0, cy, 0, pw, pd, ph)                        # hypervisor plate
    thread([(vx, vy, 0), (0, py, 0), (0, py, ph), (0, cy + vm / 2, ph)])
    for x, gold in [(-76, False), (0, True), (76, False)]:
        col = GOLD if gold else WHITE
        s.cbox(x, cy, ph, vm, vm, vh, top=col, left=col, cls="sv-gd sv-gd1" if gold else None)
        parts.window_bar(s, x, cy + vm / 2, ph + vh, vm, MIN, DOT)
        if x > 0:
            crack(x, cy, vm, ph + vh)          # a vulnerable VM beside the confidential one
        keep(1, [(x - vm / 2, cy - vm / 2, ph + vh), (x + vm / 2, cy - vm / 2, ph + vh),
                 (x + vm / 2, cy + vm / 2, ph + vh)])
    EXIT[1] = (0, cy - 6, ph + vh)          # just behind the centre of the gold VM's top
    keep(1, [(-pw / 2, cy - pd / 2, ph), (pw / 2, cy - pd / 2, ph)])


def models():
    at(2)
    vx, vy = via(2)
    inp = [(-70, 40), (0, 40), (70, 40)]
    hid = [(-70, 5), (0, 5), (70, 5)]
    out = (0, -30)
    path = [inp[1], hid[0], out]
    for a in inp:
        for b in hid:
            if (a, b) != (path[0], path[1]):
                s.line([(a[0], a[1], 0), (b[0], b[1], 0)])
    for b in hid:
        if b != path[1]:
            s.line([(b[0], b[1], 0), (out[0], out[1], 0)])
    # the inference path: part of the cardinal thread, from the via through two nodes to the output
    thread([(vx, vy, 0)] + [(x, y, 0) for x, y in path])
    r, h = 16, 20
    nodes = sorted(hid + inp, key=lambda q: q[0] + q[1])        # back to front
    back = [q for q in nodes if q[0] + q[1] < out[0] + out[1]]
    front = [q for q in nodes if q not in back]
    on_path = {path[0]: "sv-nd sv-nd1", path[1]: "sv-nd sv-nd2"}
    for x, y in back:
        s.cyl(x, y, 0, 12, 8, cls=on_path.get((x, y)))
    sx, sy0, sy1, rx = s.cyl(out[0], out[1], 0, r, h, top=GOLD, side=GOLD, cls="sv-gd sv-gd2")
    STOPS["check"] = parts.check_on_cyl(s, sx, sy1, R2 * 0.5 * r, h, 15, 2.6, cls="sv-ck")
    for x, y in front:
        s.cyl(x, y, 0, 12, 8, cls=on_path.get((x, y)))
    EXIT[2] = (out[0], out[1], h)
    keep(2, [(out[0] - r, out[1] - r, h), (-70 - 12, 5 - 12, 8), (70 - 12, 5 - 12, 8)])


def gear_frame(cx, cy, z, r, h, rot, cls, sw=2.4):
    """The gear of parts.gear turned by rot, as one hidden group: the side faces that face the viewer
    joined in one ink path (all wound the same way, so their overlaps stay filled), the white top and
    the hole. It looks like the gear drawn by parts.gear, whose other faces are always hidden."""
    pts = parts.gear_outline(cx, cy, r, rot=rot)
    quads = []
    for k in range(len(pts)):
        (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % len(pts)]
        if (y1 - y0) - (x1 - x0) <= 1e-9:      # the outward normal (dy, -dx) points away from the viewer
            continue
        q = [s.P(*p, track=False) for p in [(x0, y0, z), (x1, y1, z), (x1, y1, z + h), (x0, y0, z + h)]]
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(q, q[1:] + q[:1]))
        if area < 0:
            q.reverse()
        quads.append("M" + " L".join(f"{f(a)},{f(b)}" for a, b in q) + " Z")
    top = " ".join(f"{f(a)},{f(b)}" for a, b in (s.P(x, y, z + h, track=False) for x, y in pts))
    hx, hy = s.P(cx, cy, z + h, track=False)
    hr = r * 0.3
    s.raw(f'<g class="{cls}" visibility="hidden">'
          f'<path d="{" ".join(quads)}" fill="{INK}" stroke="{INK}" stroke-width="{f(sw)}" stroke-linejoin="round"/>'
          f'<polygon points="{top}" fill="{WHITE}" stroke="{INK}" stroke-width="{f(sw)}" stroke-linejoin="round"/>'
          f'<ellipse cx="{f(hx)}" cy="{f(hy)}" rx="{f(R2 * C * hr)}" ry="{f(R2 * 0.5 * hr)}" fill="{WHITE}" '
          f'stroke="{INK}" stroke-width="{f(MIN)}" class="sv-d"/></g>')


def agents():
    at(3)
    vx, vy = via(3)
    a, ah = 56, 54
    ax, cy = -24, -12
    cx, ccy, c = 80, -30, 48
    thread([(vx, vy, 0), (vx, cy + a / 2, 0)])
    # the tool sits behind and to the right of the agent, so the two never overlap on screen
    parts.cage(s, cx, ccy, c, False)
    s.raw('<g class="sv-gr sv-gr0">')
    parts.gear(s, cx, ccy, 0, 17, 9, sw=2.4)
    s.raw('</g>')
    for k in range(1, GEAR_FRAMES + 1):
        gear_frame(cx, ccy, 0, 17, 9, k * (2 * math.pi / 8) / (GEAR_FRAMES + 1), f"sv-gr sv-gr{k}")
    parts.cage(s, cx, ccy, c, True)
    s.line([(ax + a / 2 + 3, ccy, 0), (cx - c / 2 - 4, ccy, 0)], dash="0.1 8", sw=DOT, cls="sv-ln")
    s.cbox(ax, cy, 0, a, a, ah, top=GOLD, left=GOLD, cls="sv-gd sv-gd3")
    s.raw('<g class="sv-sp sv-sp0">')
    parts.spark(s, ax + 1, cy + a / 2, ah * 0.5, 18)
    s.raw('</g>')
    for k, grow in enumerate(SPARK_FRAMES, 1):
        s.raw(f'<g class="sv-sp sv-sp{k}" visibility="hidden">')
        parts.spark(s, ax + 1, cy + a / 2, ah * 0.5, 18, grow=grow)
        s.raw('</g>')


LABELS = ["Hardware", "Systems", "Models", "Agents"]   # research.json theme `layer`
NUM = ["I", "II", "III", "IV"]


LABEL_W = {  # Karla bold label widths (numeral, two spaces, name), measured in Chrome, plus a margin
    "desktop": [111, 106, 99, 95],     # at 20px (numerals 14px)
    "phone": [151, 146, 137, 132],     # at 27px (numerals 24px), the size below 560px
}
LABEL_BOX = []


def label(i):
    at(i)
    t = T0 if i == 0 else T
    sx, sy = s.P(-LX / 2, LY / 2, -t / 2, track=False)
    x = sx - 22
    s.raw(f'<text class="sv-lb sv-l{i}" x="{f(x)}" y="{f(sy + 7)}" text-anchor="end">'
          f'<tspan class="sv-nm" fill="{RED}">{NUM[i]}</tspan>&#160;&#160;{LABELS[i]}</text>')
    LABEL_BOX.append((x, sy - 16, sy + 10, i))


# ---------------------------------------------------------------- compose
# Each layer is a group (the same painting order as without groups): its slab, its objects and the
# riser up to the next layer, which the next slab covers.
layer_fns = [hardware, systems, models, agents]
for i in range(4):
    s.raw(f'<g class="sv-ly sv-l{i}">')
    slab(i)
    layer_fns[i]()
    if i < 3:
        riser(i)
    s.raw('</g>')
for i in range(4):
    label(i)


def hull(points):
    pts = sorted(set(points))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def clearance(p, poly):
    """signed distance from p to the convex polygon: positive outside (visible), negative inside"""
    n = len(poly)
    crosses = []
    best = 1e9
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        L = math.hypot(ex, ey)
        crosses.append((p[0] - a[0]) * ey - (p[1] - a[1]) * ex)
        t = max(0, min(1, ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / (L * L)))
        best = min(best, math.hypot(p[0] - a[0] - t * ex, p[1] - a[1] - t * ey))
    inside = all(c >= 0 for c in crosses) or all(c <= 0 for c in crosses)
    return -best if inside else best


# With --motion, standard output is the stylesheet block alone; everything else goes to stderr.
INFO = sys.stderr if "--motion" in sys.argv else sys.stdout

if "--check" in sys.argv:
    for i in range(3):
        at(i + 1)
        corners = [s.P(x, y, z, track=False) for x in (-LX / 2, LX / 2) for y in (-LY / 2, LY / 2)
                   for z in (-T, 0)]
        poly = hull(corners)
        margins = [clearance(p, poly) for p in KEEP[i]]
        print(f"layer {i} under {i + 1}: min clearance {min(margins):.1f}", file=INFO)


# ---------------------------------------------------------------- motion timing
# One loop of LOOP seconds; the stylesheet's keyframes have the same length, and each hook starts
# its keyframes after a delay, so this is the whole timetable. Times are seconds from the start of a
# loop; the first loop starts START seconds after the script starts the motion, once the one-time
# intro (the layers lifting apart a little and settling) is over. The pulse moves at SPEED units a
# second (about as many pixels on a desktop) through every piece of the thread, hidden parts
# included; it rests in the confidential VM and in the output node while they light up.
TIMING = {
    "LOOP": 8.0,        # s; style.css: animation-duration of every looping hook
    "START": 1.2,       # s; after the intro
    "SPEED": 170.0,     # units per second
    "PULSE": 36,        # units; the length of the pulse's dash
    "LEAVE": 0.25,      # s; the root of trust lights before the pulse leaves it
    "VM": 0.3,          # s; the pulse passes through the confidential VM
    "NODE": 0.5,        # s; and through the verified output node, while its check draws in
    "CHECK_LEAD": 0.6,  # s; the old check fades out this long before the new one draws in
    "FRAME": 0.1,       # s; each hidden frame of the spark and the gear (style.css: vision-frame-*)
}


def polylen(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def timetable():
    tm = TIMING
    v = tm["SPEED"]
    ev = {"rt": 0.0, "gd0": 0.0}
    t = tm["LEAVE"]
    lens = [polylen(p) for p in CHAIN]
    ev["pu1"] = t; t += lens[0] / v                       # up from the root of trust
    ev["vi1"] = ev["pu2"] = t; t += lens[1] / v           # across the hypervisor to the VM
    ev["gd1"] = t; t += tm["VM"]
    ev["pu3"] = t; t += lens[2] / v
    ev["vi2"] = ev["pu4"] = t                             # the inference path
    inference = CHAIN[3]
    to_node = [polylen(inference[:k + 1]) for k in range(len(inference))]
    node_r = R2 * C * 12                                  # the node's top ellipse, half its width
    ev["nd1"] = t + (to_node[1] - node_r) / v
    ev["nd2"] = t + (to_node[2] - node_r) / v
    t += lens[3] / v
    ev["gd2"] = t; ev["ck"] = t - tm["CHECK_LEAD"]; t += tm["NODE"]
    ev["pu5"] = t; t += lens[4] / v
    ev["vi3"] = ev["pu6"] = t; t += lens[5] / v
    ev["gd3"] = t                                         # the agent
    ev["sp0"] = t + 0.1                                   # its spark twinkles
    for k in range(1, len(SPARK_FRAMES) + 1):
        ev[f"sp{k}"] = ev["sp0"] + (k - 1) * tm["FRAME"]
    ev["ln"] = t + 0.35                                   # it calls its tool
    ev["gr0"] = t + 0.95                                  # the gear turns a notch
    for k in range(1, GEAR_FRAMES + 1):
        ev[f"gr{k}"] = ev["gr0"] + (k - 1) * tm["FRAME"]
    ev["cr"] = ev["gr0"] + 0.75                           # the crack flickers
    return ev, lens


if "--motion" in sys.argv:
    # The block of style.css between "make_vision.py --motion: begin" and "end": the pulse's keyframes
    # (every piece uses them; a piece shorter than the longest one is simply passed sooner) and the
    # delay of every hook. Between its runs the pulse's dash lies off the path (before its start, then
    # past the end of the longest piece), so nothing but the dash offset changes.
    ev, lens = timetable()
    tm = TIMING
    travel = math.ceil(max(lens)) + tm["PULSE"] + 4          # the tail clears the longest piece
    pct = 100 * travel / tm["SPEED"] / tm["LOOP"]
    print("/* make_vision.py --motion: begin. Generated by python3 design/vision/make_vision.py --motion;")
    print(f"   loop {tm['LOOP']:g} s, the first one {tm['START']:g} s after the motion starts; the pulse, "
          f"{tm['PULSE']} units long, moves {tm['SPEED']:g} units/s along")
    print("   thread pieces of " + ", ".join(f"{x:.0f}" for x in lens) + " units. */")
    # one dash, then a gap longer than the whole run, so no second dash ever reaches a piece
    print(f".vision[data-motion] .vision-sv-pu {{ stroke-dasharray: {tm['PULSE']}px {max(600, travel + 50)}px; "
          f"stroke-dashoffset: {tm['PULSE'] + 1}px; }}")
    print("@keyframes vision-pulse {")
    print(f"  0% {{ stroke-dashoffset: {tm['PULSE'] + 1}px; }}")
    print(f"  {pct:.2f}%, 100% {{ stroke-dashoffset: {tm['PULSE'] + 1 - travel}px; }}")
    print("}")
    for name, t in sorted(ev.items(), key=lambda kv: (kv[1], kv[0])):
        print(f".vision[data-motion] .vision-sv-{name} {{ animation-delay: {tm['START'] + t:.2f}s; }}")
    print(f"/* make_vision.py --motion: end (the last event starts {max(ev.values()):.2f} s into the loop; "
          f"the check is {STOPS['check']:.1f} units long) */")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out = args[0] if args else os.path.join(HERE, "vision.svg")

# viewBox: the drawing plus the labels at their larger phone size (they are right-aligned, so they grow
# to the left); the right side gets the same slack, so that on desktops, where the labels are
# smaller, labels and drawing together sit centred in the column.
PAD = 14
xs = [p[0] for p in s.pts]; ys = [p[1] for p in s.pts]
ys += [y for _, y0, y1, _ in LABEL_BOX for y in (y0, y1)]
left_phone = min([min(xs)] + [x - LABEL_W["phone"][i] for x, _, _, i in LABEL_BOX])
left_desk = min([min(xs)] + [x - LABEL_W["desktop"][i] for x, _, _, i in LABEL_BOX])
right = max(xs) + (left_desk - left_phone)
VB = (left_phone - PAD, min(ys) - PAD, right - left_phone + 2 * PAD, max(ys) - min(ys) + 2 * PAD)
style = (".sv-lb{font-family:Karla,'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:20px;"
         "font-weight:700;fill:%s}.sv-nm{font-size:14px;letter-spacing:1px}"
         "@media (max-width:560px){.sv-lb{font-size:27px}.sv-nm{font-size:24px}"
         ".sv-o{stroke-width:4.2px}.sv-d{stroke-width:2.4px}.sv-t{stroke-width:7.5px}.sv-p{stroke-width:4.4px}}"
         % INK)
TITLE = "SEPT Lab vision: trustworthy computing, from hardware to AI agents"
DESC = ("Four isometric layers rise from bottom left to top right. I Hardware: a chip whose gold enclave "
        "holds a red root of trust. II Systems: three virtual machines on a hypervisor; the middle one is "
        "gold, a confidential VM, and a red crack splits the one on the right, a vulnerability. III Models: a small neural network whose red inference path ends in a "
        "gold output node marked with a check. IV Agents: a gold agent block marked with the AI spark, "
        "linked to a tool isolated in a wireframe cage. Gold marks what is protected on each layer; one "
        "red thread, the chain of trust, rises from the root of trust through every gold element to the "
        "agent.")
open(out, "w").write(s.svg(TITLE, DESC, vb=VB, style=style, uid="sept-vision"))
x, y, w, h = VB
print(out, f"viewBox {x:.1f} {y:.1f} {w:.1f} {h:.1f}  aspect {w / h:.3f}", file=INFO)
