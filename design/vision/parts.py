"""Shared isometric parts used by both the vision image and the research icons."""
import math
from iso import INK, GOLD, RED, WHITE, R2, S as ISO_S


def extrude_poly(s, pts2, z, h, top=WHITE, sw=None):
    """flat polygon (x,y) extruded from z to z+h: ink underside and sides, then the top face"""
    sw = s.sw if sw is None else sw
    s.poly([(x, y, z) for x, y in pts2], fill=INK, stroke=INK, sw=sw)
    for k in range(len(pts2)):
        (x0, y0), (x1, y1) = pts2[k], pts2[(k + 1) % len(pts2)]
        s.poly([(x0, y0, z), (x1, y1, z), (x1, y1, z + h), (x0, y0, z + h)], fill=INK, stroke=INK, sw=sw)
    s.poly([(x, y, z + h) for x, y in pts2], fill=top, stroke=INK, sw=sw)


def gear_outline(cx, cy, r, teeth=8, rot=0.0):
    """the plan outline of a gear, turned by rot radians (one tooth is 2 pi / teeth)"""
    pts = []
    n = teeth * 4
    for k in range(n):
        a = 2 * math.pi * k / n + math.pi / n + rot
        rr = r if (k % 4) in (0, 1) else r * 0.72
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def gear(s, cx, cy, z, r, h, teeth=8, hole=True, sw=None, hole_sw=None):
    extrude_poly(s, gear_outline(cx, cy, r, teeth), z, h, sw=sw)
    if hole:
        s.disc(cx, cy, z + h, r * 0.3, fill=WHITE, stroke=INK, sw=hole_sw or s.swd)


def cage(s, x, y, c, front, sw=None, z=0, ch=None):
    """wireframe isolation box (side c, height ch) centred at (x, y) on z. Draw the back edges
    (front=False) before the contents and the front edges (front=True) after them."""
    ch = c if ch is None else ch
    X0, X1, Y0, Y1, Z0, Z1 = x - c / 2, x + c / 2, y - c / 2, y + c / 2, z, z + ch
    L = lambda pts: s.line(pts, sw=sw)
    if not front:
        L([(X0, Y0, Z0), (X0, Y0, Z1)]); L([(X0, Y0, Z1), (X1, Y0, Z1)]); L([(X0, Y0, Z1), (X0, Y1, Z1)])
        L([(X0, Y1, Z0), (X0, Y0, Z0), (X1, Y0, Z0)])
    else:
        L([(X1, Y1, Z0), (X1, Y1, Z1)]); L([(X0, Y1, Z0), (X0, Y1, Z1)]); L([(X1, Y0, Z0), (X1, Y0, Z1)])
        L([(X0, Y1, Z0), (X1, Y1, Z0), (X1, Y0, Z0)])
        L([(X0, Y1, Z1), (X1, Y1, Z1), (X1, Y0, Z1)])


def spark(s, cx, y, cz, R, p=2.6, fill=INK, small=True, grow=(1, 1)):
    """The four-point 'AI spark', painted on a +Y face (the plane y = const) centred at (cx, cz).
    A second, smaller spark sits at its upper right, as in the common AI mark. grow scales the big
    and the small star about their own centres (the vision image's twinkle)."""
    def star(ux, uz, r):
        pts = []
        for k in range(64):
            t = 2 * math.pi * k / 64
            c, sn = math.cos(t), math.sin(t)
            u = r * math.copysign(abs(c) ** p, c)
            v = r * math.copysign(abs(sn) ** p, sn)
            pts.append((ux + u, y, uz + v))
        s.poly(pts, fill=fill, stroke=None)
    star(cx - R * 0.12, cz - R * 0.1, R * grow[0])
    if small:
        star(cx + R * 0.78, cz + R * 0.72, R * 0.38 * grow[1])


def check_on_cyl(s, sx, sy1, ry, h, size, sw, stroke=INK, cls=None):
    """An upright check mark (screen space) on the front of a cylinder's side, given the screen
    centre x, the screen y of the top ellipse's centre, its ry and the cylinder height. Returns
    its length."""
    cy = sy1 + ry + h * 0.5 + size * 0.06
    w = size
    pts = [(sx - 0.5 * w, cy - 0.02 * w), (sx - 0.14 * w, cy + 0.3 * w), (sx + 0.52 * w, cy - 0.36 * w)]
    d = (f"M{pts[0][0]:.1f},{pts[0][1]:.1f} L{pts[1][0]:.1f},{pts[1][1]:.1f} "
         f"L{pts[2][0]:.1f},{pts[2][1]:.1f}")
    s.path2(d, stroke=stroke, sw=sw, cls=cls)
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def chip(s, cx, cy, w, ch, n=6, pitch=13, pin=(4, 8, 3), inset=14, pin_sw=None, z=0):
    """A square package with gull-wing-like pads on all four sides; returns the pin offsets."""
    pw, pl, phh = pin
    ks = [(k - (n - 1) / 2) * pitch for k in range(n)]
    for k in ks:      # back and left pins first (mostly hidden)
        s.cbox(cx - w / 2 - pl / 2, cy + k, z, pl, pw, phh, sw=pin_sw)
        s.cbox(cx + k, cy - w / 2 - pl / 2, z, pw, pl, phh, sw=pin_sw)
    s.cbox(cx, cy, z, w, w, ch)
    for k in ks:
        s.cbox(cx + k, cy + w / 2 + pl / 2, z, pw, pl, phh, sw=pin_sw)
        s.cbox(cx + w / 2 + pl / 2, cy + k, z, pl, pw, phh, sw=pin_sw)
    if inset:
        i = inset
        s.poly([(cx - w / 2 + i, cy - w / 2 + i, z + ch), (cx + w / 2 - i, cy - w / 2 + i, z + ch),
                (cx + w / 2 - i, cy + w / 2 - i, z + ch), (cx - w / 2 + i, cy + w / 2 - i, z + ch)],
               fill="none", sw=s.swd)
    return ks


def window_bar(s, x, y1, z_top, a, sw_line, sw_dot, inset=11, dots=(7, 14)):
    """the 'window' title bar (a rule and two dots) on the +Y face of a box whose front plane is y1"""
    s.line([(x - a / 2, y1, z_top - inset), (x + a / 2, y1, z_top - inset)])
    for dx in dots:
        s.line([(x - a / 2 + dx, y1, z_top - inset / 2), (x - a / 2 + dx + 0.01, y1, z_top - inset / 2)],
               sw=sw_dot)
