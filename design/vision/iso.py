"""Tiny isometric SVG toolkit for the SEPT Lab vision image and research icons.

True isometric: plan X runs down-right at 30 degrees, plan Y down-left at 30 degrees, Z straight up.
Shading rule everywhere (after comsec.ethz.ch's icons): top faces and +Y faces white (or gold for the
protected element), +X faces solid ink.

A Scene can tag strokes by weight with CSS classes (`wcls`), so that an SVG's own <style> can thicken
them on small screens. Class names are prefixed ("sv-") so they never collide with page styles; the
site's build prefixes them again when it inlines the file. The drawing functions also take an extra
class (`cls`), which the vision image uses as hooks for its motion; it changes nothing by itself.
"""
import math

C = math.cos(math.radians(30))
S = 0.5
R2 = math.sqrt(2)

INK = "#23261f"     # near-black olive (the logo's tree is #262A20)
GOLD = "#EBB840"    # the logo's sun
RED = "#B22A22"     # cardinal
WHITE = "#ffffff"


def f(v):
    s = f"{v:.1f}"
    s = "0" if s in ("-0.0", "0.0") else s
    return s[:-2] if s.endswith(".0") else s


class Scene:
    def __init__(self, sw=3.0, swd=1.6, wcls=None):
        self.els = []
        self.pts = []
        self.off = (0.0, 0.0, 0.0)
        self.sw = sw      # outline weight
        self.swd = swd    # detail weight
        self.wcls = wcls or {}   # stroke weight -> CSS class

    # --- projection -------------------------------------------------------
    def P(self, x, y, z, track=True):
        ox, oy, oz = self.off
        x, y, z = x + ox, y + oy, z + oz
        sx = (x - y) * C
        sy = (x + y) * S - z
        if track:
            self.pts.append((sx, sy))
        return sx, sy

    def raw(self, s):
        self.els.append(s)

    def _cls(self, sw, extra=None):
        names = [n for n in (self.wcls.get(round(sw, 2)) if sw is not None else None, extra) if n]
        return f' class="{" ".join(names)}"' if names else ""

    def _stroke(self, stroke, sw):
        return f' stroke="{stroke}" stroke-width="{f(sw)}"' if stroke else ""

    # --- primitives -------------------------------------------------------
    def poly(self, pts3, fill=WHITE, stroke=INK, sw=None, cls=None, close=True):
        sw = self.sw if sw is None else sw
        pts = [self.P(*p) for p in pts3]
        d = " ".join(f"{f(a)},{f(b)}" for a, b in pts)
        tag = "polygon" if close else "polyline"
        st = self._stroke(stroke, sw) + (' stroke-linejoin="round"' if stroke else "")
        self.raw(f'<{tag} points="{d}" fill="{fill}"{st}{self._cls(sw if stroke else None, cls)}/>')

    def flat(self, pts2, fill=INK):
        """a filled 2D polygon in screen coordinates (already projected)"""
        d = " ".join(f"{f(a)},{f(b)}" for a, b in pts2)
        self.raw(f'<polygon points="{d}" fill="{fill}"/>')

    def line(self, pts3, stroke=INK, sw=None, dash=None, cap="round", cls=None):
        sw = self.swd if sw is None else sw
        pts = [self.P(*p) for p in pts3]
        d = "M" + " L".join(f"{f(a)},{f(b)}" for a, b in pts)
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{f(sw)}" '
                 f'stroke-linecap="{cap}" stroke-linejoin="round"{ds}{self._cls(sw, cls)}/>')

    def path2(self, d, stroke=INK, sw=None, fill="none", cap="round", cls=None):
        """a raw 2D path in screen coordinates"""
        sw = self.swd if sw is None else sw
        self.raw(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" '
                 f'stroke-linecap="{cap}" stroke-linejoin="round"{self._cls(sw, cls)}/>')

    def box(self, x, y, z, dx, dy, dz, top=WHITE, left=WHITE, right=INK, sw=None, stroke=INK, cls=None):
        """Axis-aligned box from (x,y,z) with size (dx,dy,dz). left = +Y face, right = +X face.
        cls goes on the left and top faces, the ones that take a colour."""
        X0, X1, Y0, Y1, Z0, Z1 = x, x + dx, y, y + dy, z, z + dz
        self.poly([(X0, Y1, Z0), (X1, Y1, Z0), (X1, Y1, Z1), (X0, Y1, Z1)], left, stroke, sw, cls=cls)
        self.poly([(X1, Y0, Z0), (X1, Y1, Z0), (X1, Y1, Z1), (X1, Y0, Z1)], right, stroke, sw)
        self.poly([(X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1), (X0, Y1, Z1)], top, stroke, sw, cls=cls)

    def cbox(self, cx, cy, z, dx, dy, dz, **kw):
        self.box(cx - dx / 2, cy - dy / 2, z, dx, dy, dz, **kw)

    def disc(self, cx, cy, z, r, fill=WHITE, stroke=INK, sw=None, cls=None):
        sw = self.sw if sw is None else sw
        sx, sy = self.P(cx, cy, z)
        self.P(cx + r, cy + r, z); self.P(cx - r, cy - r, z)
        self.raw(f'<ellipse cx="{f(sx)}" cy="{f(sy)}" rx="{f(R2 * C * r)}" ry="{f(R2 * S * r)}" '
                 f'fill="{fill}"{self._stroke(stroke, sw)}{self._cls(sw if stroke else None, cls)}/>')

    def cyl(self, cx, cy, z, r, h, top=WHITE, side=WHITE, stroke=INK, sw=None, cls=None):
        sw = self.sw if sw is None else sw
        sx, sy0 = self.P(cx, cy, z)
        _, sy1 = self.P(cx, cy, z + h)
        rx, ry = R2 * C * r, R2 * S * r
        self.P(cx + r, cy + r, z); self.P(cx - r, cy - r, z + h)
        d = (f"M{f(sx - rx)},{f(sy1)} L{f(sx - rx)},{f(sy0)} "
             f"A{f(rx)},{f(ry)} 0 0 0 {f(sx + rx)},{f(sy0)} L{f(sx + rx)},{f(sy1)} Z")
        self.raw(f'<path d="{d}" fill="{side}" stroke="{stroke}" stroke-width="{f(sw)}" '
                 f'stroke-linejoin="round"{self._cls(sw, cls)}/>')
        self.raw(f'<ellipse cx="{f(sx)}" cy="{f(sy1)}" rx="{f(rx)}" ry="{f(ry)}" fill="{top}" '
                 f'stroke="{stroke}" stroke-width="{f(sw)}"{self._cls(sw, cls)}/>')
        return sx, sy0, sy1, rx

    # --- output -----------------------------------------------------------
    def bbox(self, pad=10):
        xs = [p[0] for p in self.pts]; ys = [p[1] for p in self.pts]
        return min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad

    def svg(self, title, desc=None, vb=None, pad=12, style="", uid="sv", decorative=False):
        x, y, w, h = vb if vb else self.bbox(pad)
        body = "\n  ".join(self.els)
        st = f"\n  <style>{style}</style>" if style else ""
        if decorative:
            head = f' aria-hidden="true" focusable="false">\n  <title>{title}</title>'
        else:
            ids = f"{uid}-t {uid}-d" if desc else f"{uid}-t"
            head = (f' role="img" aria-labelledby="{ids}">\n  <title id="{uid}-t">{title}</title>'
                    + (f'\n  <desc id="{uid}-d">{desc}</desc>' if desc else ""))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(x)} {f(y)} {f(w)} {f(h)}" '
                f'width="100%"{head}{st}\n  {body}\n</svg>\n')
