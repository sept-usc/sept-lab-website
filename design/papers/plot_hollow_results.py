#!/usr/bin/env python3
"""Plot the normalized Hollow-LLM timings from Table 2, paper §5.

Requires Matplotlib. Run with a Python environment containing it:
    python3 design/papers/plot_hollow_results.py

Outputs editable SVG text in desktop (900 × 650) and mobile (450 × 1040)
compositions. Optional --preview-dir writes PNGs for visual inspection.
The three time measurements have separate inner-model baselines: their
ratios are comparable within each panel, not as absolute time across panels.
"""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator

OUT = Path(__file__).resolve().parents[2] / 'assets/img/papers'
MODELS = ['Inner model\n6L / 512', 'Hollow A+B\n12L / 1024', 'Honest larger\n12L / 1024']
PHASES = [
    ('Prefill — serving', [1.0, 1.0, 2.4]),
    ('Decode — serving', [1.0, 1.0, 3.1]),
    ('Proof generation', [1.0, 4.81, 4.74]),
]
COLORS = ['#ffffff', '#e6c879', '#d2d2d2']
INK, MUTED, RULE = '#252525', '#656565', '#d7d7d7'

plt.rcParams.update({
    'svg.fonttype': 'none',
    'svg.hashsalt': 'hollow-llm-table-2',
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Liberation Sans', 'DejaVu Sans'],
    'text.color': INK,
    'axes.labelcolor': INK,
    'xtick.color': MUTED,
    'ytick.color': INK,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
})


def value_label(value):
    return f'{value:g}×'


def accessible_svg(path, width, height):
    # Retain Matplotlib's SVG and text elements, adding an accessible description
    # and explicit pixel dimensions that match the site's responsive picture.
    text = path.read_text(encoding='utf-8')
    text = text.replace(f'width="{width}pt" height="{height}pt"',
                        f'width="{width}" height="{height}"', 1)
    marker = 'xmlns:xlink="http://www.w3.org/1999/xlink"'
    text = text.replace(marker, marker + ' role="img" aria-labelledby="chart-title chart-desc"', 1)
    start = text.index('>', text.index('<svg')) + 1
    metadata = ('\n<title id="chart-title">Hollow-LLM serving and proof-generation time</title>'
                '\n<desc id="chart-desc">Time is normalized to the inner model separately for each phase. '
                'The inner model has 6 layers and hidden dimension 512. Hollow A+B and the honest larger '
                'reference both declare 12 layers and dimension 1024. Prefill ratios are 1, 1, and 2.4; '
                'decode ratios are 1, 1, and 3.1; proof-generation ratios are 1, 4.81, and 4.74. '
                'Serving savings do not imply cheaper proofs. Source: Hollow-LLM Table 2.</desc>')
    text = text[:start] + metadata + text[start:]
    ET.fromstring(text)
    path.write_text(text, encoding='utf-8')


def render(mobile=False, preview_dir=None):
    width, height = (450, 1040) if mobile else (900, 650)
    fig = plt.figure(figsize=(width / 72, height / 72), dpi=72)

    def text(x, y, label, size=18, **kwargs):
        return fig.text(x / width, 1 - y / height, label, fontsize=size,
                        va='top', ha='left', **kwargs)

    if mobile:
        text(20, 20, 'Hollow-LLM results', 24, weight='bold')
        text(20, 64, 'Time relative to the inner model', 18)
        text(20, 91, '6 layers · hidden dimension 512', 17, color=MUTED)
        panel_tops, panel_height = [185, 458, 731], 175
        title_tops = [146, 419, 692]
        left, right = 146, 53
        label_size, tick_size, value_size = 17, 15, 17
    else:
        text(28, 18, 'Hollow-LLM: serving cost and proving cost', 25, weight='bold')
        text(28, 62, 'Time relative to the 6-layer, 512-dimensional inner model', 19, color=MUTED)
        panel_tops, panel_height = [137, 300, 463], 102
        title_tops = [106, 269, 432]
        left, right = 235, 70
        label_size, tick_size, value_size = 16, 15, 18

    for (phase, values), top, title_top in zip(PHASES, panel_tops, title_tops):
        text(20 if mobile else 28, title_top, phase, 21, weight='bold')
        ax = fig.add_axes([left / width, (height - top - panel_height) / height,
                           (width - left - right) / width, panel_height / height])
        ax.barh([0, 1, 2], values, height=0.54, color=COLORS,
                edgecolor=INK, linewidth=0.9, zorder=3)
        ax.set_ylim(2.65, -0.65)
        ax.set_xlim(0, 5.25)
        labels = MODELS if mobile else ['Inner · 6L / 512', 'Hollow A+B · 12L / 1024', 'Honest larger · 12L / 1024']
        ax.set_yticks([0, 1, 2], labels, fontsize=label_size, linespacing=1.08)
        ax.tick_params(axis='y', length=0, pad=10)
        ax.xaxis.set_major_locator(FixedLocator([0, 1, 2, 3, 4, 5]))
        ax.set_xticklabels(['0', '1×', '2×', '3×', '4×', '5×'], fontsize=tick_size)
        ax.tick_params(axis='x', length=3, width=0.7, pad=5)
        ax.grid(axis='x', color=RULE, linewidth=0.7, zorder=0)
        for side in ['top', 'left', 'right']:
            ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color(RULE)
        for row, value in enumerate(values):
            ax.text(value + 0.10, row, value_label(value), fontsize=value_size,
                    color=INK, va='center', ha='left', weight='bold', clip_on=False)

    if mobile:
        text(20, 974, 'Each phase uses its own 1× baseline.', 17, color=MUTED)
        text(20, 1003, 'Serving savings ≠ cheaper proofs.', 17, weight='bold')
    else:
        text(28, 611, 'Each phase uses its own baseline. Serving savings do not imply cheaper proofs.', 18)

    filename = 'hollow-llm-results' + ('-mobile' if mobile else '')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (filename + '.svg')
    fig.savefig(path, format='svg', dpi=72, metadata={'Date': None})
    accessible_svg(path, width, height)
    if preview_dir:
        preview_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(preview_dir / (filename + '.png'), dpi=72)
    plt.close(fig)
    print(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-dir', type=Path)
    args = parser.parse_args()
    render(preview_dir=args.preview_dir)
    render(mobile=True, preview_dir=args.preview_dir)
