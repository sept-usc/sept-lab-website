#!/usr/bin/env python3
"""Original, editable SVG overviews of FLASH (§5), ARGUS (§IV), and Hollow-LLM (§3–5).

Run from any directory: python3 design/papers/make_figures.py
Only the standard library is needed. Desktop and mobile compositions carry
identical mechanisms; positions and line breaks are composed for each size.
"""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'assets/img/papers'
INK, MUTED, RED, GOLD = '#252525', '#656565', '#990000', '#906000'
RULE, TINT, WARM, GRAY = '#d7d7d7', '#fcf6f5', '#fcf6e8', '#f6f6f6'
TRUST_STROKE, TRUST_FILL, DIRTY_FILL = '#000000', '#edf7ee', '#c9e5cc'


class Figure:
    def __init__(self, width, height, title, description):
        self.parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="{MUTED}"/></marker></defs>
<rect width="{width}" height="{height}" fill="#fff"/>
<g font-family="Arial, Helvetica, sans-serif">''']

    def box(self, x, y, w, h, fill='white', stroke=RULE, dashed=False, r=6):
        dash = ' stroke-dasharray="7 5"' if dashed else ''
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>')

    def text(self, x, y, lines, size=20, color=INK, bold=False, anchor='start', leading=None):
        if isinstance(lines, str): lines = [lines]
        for i, line in enumerate(lines):
            self.parts.append(f'<text x="{x}" y="{y + i * (leading or size * 1.4)}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(line)}</text>')

    def line(self, x1, y1, x2, y2, color=RULE, arrow=False, dashed=False):
        end = ' marker-end="url(#arrow)"' if arrow else ''
        dash = ' stroke-dasharray="5 5"' if dashed else ''
        self.parts.append(f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{color}" stroke-width="1.7"{end}{dash}/>')

    def check(self, x, y):
        self.parts.append(f'<path d="M{x} {y}l5 5 10-12" fill="none" stroke="{TRUST_STROKE}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')

    def pages(self, x, y, size=24):
        for i in range(5):
            self.box(x+i*(size+8), y, size, size+8, DIRTY_FILL if i in (1,3) else 'white', TRUST_STROKE, r=2)
            if i in (1,3): self.line(x+i*(size+8)+6,y+12,x+i*(size+8)+size-6,y+12,TRUST_STROKE)

    def matrix(self, x, y):
        for row in range(3):
            for col in range(5):
                self.box(x+col*24, y+row*22, 16, 14, '#e8e8e8' if (row+col)%2 else 'white', RULE, r=1)

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT/name).write_text('\n'.join(self.parts)+ '\n</g></svg>\n', encoding='utf-8')


def flash(mobile=False):
    desc = ('FLASH preserves GPU copy-engine ciphertext, wraps the GPU session key with the CPU checkpoint state, '
            'and stores an authenticated snapshot on untrusted storage. A trusted remote attestation service supplies '
            'checkpoint key and freshness state. Concurrent copying and write-fault tracking leave a short stop-and-copy phase.')
    f = Figure(450 if mobile else 900, 1040 if mobile else 650, 'FLASH checkpoint pipeline', desc)
    if not mobile:
        f.text(28, 34, 'FLASH: preserve ciphertext, shorten the pause', 25, bold=True)
        f.box(326, 68, 546, 74, TRUST_FILL, TRUST_STROKE, dashed=True)
        f.text(347, 96, 'Trusted remote attestation service', 21, TRUST_STROKE, True)
        f.text(347, 124, 'Checkpoint key + freshness state', 19)
        f.line(463, 142, 463, 171, MUTED, True, True)
        f.box(28, 182, 240, 240, TRUST_FILL, TRUST_STROKE)
        f.text(48, 218, 'Trusted GPU TEE', 23, TRUST_STROKE, True)
        f.text(48, 249, 'LLM + KV cache', 21)
        f.pages(48, 270, 28)
        f.text(48, 336, ['Write faults track', 'dirty 2 MB pages'], 20)
        f.text(48, 401, 'Copy engine encrypts', 18, MUTED)
        f.line(273, 300, 317, 300, MUTED, True)
        f.box(326, 182, 274, 240, TRUST_FILL, TRUST_STROKE)
        f.text(346, 218, 'Trusted CPU CVM', 23, TRUST_STROKE, True)
        f.text(346, 255, ['GPU ciphertext', 'kept as is'], 21, bold=True)
        f.line(346, 301, 580, 301, TRUST_STROKE)
        f.text(346, 330, ['CPU state + wrapped', 'GPU key + authenticated', 'snapshot metadata'], 19, leading=28)
        f.line(606, 300, 646, 300, MUTED, True)
        f.box(656, 182, 216, 240, GRAY, MUTED, dashed=True)
        f.text(677, 217, ['Untrusted', 'storage'], 23, bold=True, leading=29)
        f.box(680, 271, 168, 75, 'white')
        f.text(764, 300, ['Encrypted', 'checkpoint'], 20, anchor='middle', leading=27)
        f.text(677, 386, ['Ciphertext +', 'protected keys'], 18, MUTED, leading=24)
        f.text(28, 468, 'Checkpoint timeline', 22, bold=True)
        f.box(28, 489, 608, 80, TINT, RULE, r=0)
        f.text(49, 519, 'Inference continues', 22, RED, True)
        f.text(49, 549, 'Concurrent copy + write-fault tracking', 20)
        f.box(636, 489, 236, 80, WARM, RULE, r=0)
        f.text(656, 519, 'Brief pause', 22, GOLD, True)
        f.text(656, 549, 'Copy final dirty delta', 19)
        f.text(28, 611, 'Static weights: save once, keep monitoring for later writes.', 19, MUTED)
    else:
        f.text(20, 32, 'FLASH checkpoint pipeline', 24, bold=True)
        f.box(20, 66, 410, 170, TRUST_FILL, TRUST_STROKE)
        f.text(40, 100, 'Trusted GPU TEE', 23, TRUST_STROKE, True)
        f.text(40, 132, 'LLM + KV cache', 20)
        f.pages(252, 117, 22)
        f.text(40, 174, ['Write faults track dirty 2 MB pages.', 'The copy engine encrypts GPU state.'], 19, leading=29)
        f.line(225, 241, 225, 273, MUTED, True)
        f.box(20, 286, 410, 262, TRUST_FILL, TRUST_STROKE)
        f.text(40, 322, 'Trusted CPU confidential VM', 23, TRUST_STROKE, True)
        f.text(40, 360, 'Keep GPU ciphertext as is', 21, bold=True)
        f.text(40, 395, ['Bundle CPU state, the wrapped GPU', 'key, and authenticated metadata.'], 19, leading=28)
        f.line(40, 442, 410, 442, TRUST_STROKE)
        f.text(40, 473, ['Checkpoint key + freshness come from', 'a trusted remote attestation service.'], 18, MUTED, leading=27)
        f.line(225, 553, 225, 585, MUTED, True)
        f.box(20, 598, 410, 120, GRAY, MUTED, dashed=True)
        f.text(40, 633, 'Untrusted storage', 23, bold=True)
        f.text(40, 667, ['Encrypted checkpoint + protected keys'], 19)
        f.text(20, 768, 'Checkpoint timeline', 22, bold=True)
        f.box(20, 788, 410, 84, TINT, RULE, r=0)
        f.text(40, 820, 'Inference continues', 21, RED, True)
        f.text(40, 850, 'Concurrent copy + write-fault tracking', 18)
        f.box(20, 872, 410, 84, WARM, RULE, r=0)
        f.text(40, 904, 'Brief pause', 21, GOLD, True)
        f.text(40, 934, 'Copy the final dirty delta', 19)
        f.text(20, 992, ['Static weights: save once,', 'keep monitoring for later writes.'], 18, MUTED, leading=26)
    f.save('flash-overview'+('-mobile' if mobile else '')+'.svg')


def argus(mobile=False):
    desc = ('An untrusted GPU performs LLM inference and exports intermediate values through untrusted shared buffers. '
            'ARGUS copies each frame into protected CPU CVM memory, checks arithmetic, cross-layer consistency, '
            'and token selection, then releases a response and signed receipt only after verification passes.')
    f = Figure(450 if mobile else 900, 1040 if mobile else 650, 'ARGUS inference verification pipeline', desc)
    if not mobile:
        f.text(28, 34, 'ARGUS: verify execution before releasing a response', 25, bold=True)
        f.text(28, 84, 'OUTSIDE THE TRUST BOUNDARY', 17, MUTED, True)
        f.box(28, 104, 220, 302, GRAY, MUTED, dashed=True)
        f.text(48, 143, ['Untrusted', 'GPU'], 24, bold=True, leading=31)
        f.matrix(48, 200)
        f.text(48, 302, ['Full LLM', 'forward pass'], 21, leading=29)
        f.text(48, 380, 'Export intermediates', 17, MUTED)
        f.line(254, 266, 291, 266, MUTED, True)
        f.box(300, 177, 168, 177, GRAY, MUTED, dashed=True)
        f.text(318, 214, ['Shared', 'buffers'], 22, bold=True, leading=29)
        f.text(318, 285, ['Untrusted', 'transfer path'], 18, MUTED, leading=27)
        f.line(474, 266, 510, 266, MUTED, True)
        f.box(520, 104, 352, 302, TRUST_FILL, TRUST_STROKE)
        f.text(540, 143, 'Trusted CPU CVM', 24, TRUST_STROKE, True)
        f.text(540, 178, ['Copy once into protected memory'], 19)
        f.line(540, 199, 852, 199, TRUST_STROKE)
        for y, label in [(237, 'Matrix-product checks'), (278, 'Nonlinear + layer checks'), (319, 'Token-selection checks')]:
            f.check(541, y-8); f.text(566, y, label, 20)
        f.text(540, 380, 'Secret randomness stays inside', 18, MUTED)
        f.line(696, 411, 696, 465, MUTED, True)
        f.text(712, 445, 'Checks pass', 18, TRUST_STROKE, True)
        f.box(520, 480, 352, 126, WARM, GOLD)
        f.text(540, 516, ['Response + signed receipt'], 22, GOLD, True)
        f.text(540, 551, ['Release after the complete', 'response has been verified.'], 20, leading=29)
        f.text(28, 496, 'The receipt binds', 22, bold=True)
        f.text(28, 531, ['Request · response · model', 'Runtime · verification policy'], 21, leading=32)
        f.text(28, 603, 'Failed checks reject the request.', 18, RED)
    else:
        f.text(20, 32, 'ARGUS verification pipeline', 24, bold=True)
        f.box(20, 66, 410, 166, GRAY, MUTED, dashed=True)
        f.text(40, 101, 'Untrusted GPU', 23, bold=True)
        f.text(40, 139, ['Full LLM forward pass', 'Export intermediate values'], 19, leading=30)
        f.matrix(281, 119)
        f.line(225, 237, 225, 269, MUTED, True)
        f.box(20, 282, 410, 112, GRAY, MUTED, dashed=True)
        f.text(40, 317, 'Untrusted shared buffers', 23, bold=True)
        f.text(40, 353, 'Copy once into protected CVM memory', 19)
        f.line(225, 399, 225, 431, MUTED, True)
        f.box(20, 444, 410, 264, TRUST_FILL, TRUST_STROKE)
        f.text(40, 480, 'Trusted CPU confidential VM', 23, TRUST_STROKE, True)
        for y, label in [(528, 'Matrix-product checks'), (569, 'Nonlinear + layer checks'), (610, 'Token-selection checks')]:
            f.check(41, y-8); f.text(68, y, label, 20)
        f.line(40, 633, 410, 633, TRUST_STROKE)
        f.text(40, 674, 'Secret randomness stays inside', 19, MUTED)
        f.line(225, 713, 225, 755, MUTED, True)
        f.text(242, 739, 'Checks pass', 18, TRUST_STROKE, True)
        f.box(20, 768, 410, 132, WARM, GOLD)
        f.text(40, 804, 'Response + signed receipt', 23, GOLD, True)
        f.text(40, 840, ['Release only after the complete', 'response has been verified.'], 19, leading=29)
        f.text(20, 942, 'Receipt: request, response, model,', 19)
        f.text(20, 970, 'runtime, and verification policy.', 19)
        f.text(20, 1014, 'Failed checks reject the request.', 18, RED)
    f.save('argus-overview'+('-mobile' if mobile else '')+'.svg')


def hollow(mobile=False):
    desc = ('Before commitment, the model owner chooses structured ghost weights for a larger declared architecture. '
            'Serving executes a small inner model. Proof generation constructs the larger circuit witness for the same output. '
            'The verifier accepts a valid proof of the committed relation, which does not measure actual serving effort.')
    f = Figure(450 if mobile else 900, 1040 if mobile else 650, 'Hollow-LLM serving and proving paths', desc)
    if not mobile:
        f.text(28, 34, 'Hollow-LLM: a larger declaration, a smaller serving path', 25, bold=True)
        f.box(28, 70, 844, 112, GRAY, MUTED, dashed=True)
        f.text(48, 106, 'Choose structured private weights, then commit', 24, bold=True)
        f.text(48, 143, 'Small inner model + identity layers or replicated coordinates', 22)
        f.line(208, 187, 208, 247, MUTED, True)
        f.line(692, 187, 692, 247, MUTED, True)
        f.text(230, 226, 'SERVE', 17, MUTED, True)
        f.text(711, 226, 'PROVE', 17, MUTED, True)
        f.box(28, 262, 360, 142, WARM, GOLD)
        f.text(48, 298, 'Execute the small inner model', 22, GOLD, True)
        f.text(48, 334, ['Identity / replica work collapses', 'on the online serving path.'], 20, leading=29)
        f.box(512, 262, 360, 142, GRAY, MUTED)
        f.text(532, 298, 'Use the larger declared circuit', 22, bold=True)
        f.text(532, 334, ['Construct its witness', 'and generate a valid proof.'], 20, leading=29)
        f.line(208, 409, 208, 448, MUTED, True)
        f.line(692, 409, 692, 448, MUTED, True)
        f.box(28, 462, 360, 112, WARM, GOLD)
        f.text(48, 499, 'Same logits and output y', 23, GOLD, True)
        f.text(48, 538, 'as the inner model', 21)
        f.box(512, 462, 360, 112, TRUST_FILL, TRUST_STROKE)
        f.check(533, 492)
        f.text(559, 499, 'Verifier accepts', 23, TRUST_STROKE, True)
        f.text(532, 538, 'Committed relation is satisfied.', 20)
        f.line(394, 520, 502, 520, MUTED, True)
        f.text(448, 503, 'same y', 17, MUTED, anchor='middle')
        f.text(28, 618, 'A valid inference proof does not measure the effort spent serving the response.', 20, MUTED)
    else:
        f.text(20, 32, 'Hollow-LLM: serving vs. proving', 24, bold=True)
        f.box(20, 66, 410, 160, GRAY, MUTED, dashed=True)
        f.text(40, 102, 'Choose and commit ghost weights', 22, bold=True)
        f.text(40, 141, ['Small inner model embedded in a', 'larger declared architecture using', 'identity layers or replicated coordinates.'], 18, leading=29)
        f.line(225, 231, 225, 269, MUTED, True)
        f.box(20, 282, 410, 132, WARM, GOLD)
        f.text(40, 318, '1. Serve using the small model', 22, GOLD, True)
        f.text(40, 354, ['Identity / replica work collapses', 'on the online serving path.'], 19, leading=28)
        f.line(225, 419, 225, 451, MUTED, True)
        f.box(20, 464, 410, 102, WARM, GOLD)
        f.text(40, 500, 'Same logits and output y', 23, GOLD, True)
        f.text(40, 536, 'as the inner model', 20)
        f.line(225, 571, 225, 603, MUTED, True)
        f.box(20, 616, 410, 140, GRAY, MUTED)
        f.text(40, 652, '2. Prove the committed relation', 22, bold=True)
        f.text(40, 689, ['Construct a witness for the larger', 'circuit; generate a valid proof for y.'], 19, leading=29)
        f.line(225, 761, 225, 793, MUTED, True)
        f.box(20, 806, 410, 130, TRUST_FILL, TRUST_STROKE)
        f.check(41, 837)
        f.text(68, 844, 'Verifier accepts', 23, TRUST_STROKE, True)
        f.text(40, 884, 'Committed relation is satisfied.', 20)
        f.text(20, 979, ['The proof does not measure the effort', 'spent serving the response.'], 19, MUTED, leading=29)
    f.save('hollow-llm-overview'+('-mobile' if mobile else '')+'.svg')


if __name__ == '__main__':
    for mobile in (False, True):
        flash(mobile)
        argus(mobile)
        hollow(mobile)
    print('Wrote six paper overview SVGs to', OUT)
