"""Plan view of the four v5 mounts as the generator builds them from the CADCraft drawing.

python 46es/tools/plot_mount_outlines.py  ->  46es/docs/mount-phase1-outline.png
Outline and pads come from model/mounts_cadcraft_phase1.dxf, fasteners from the
document parameters and pin reliefs from the switch layout (tools/mounts_v5.py).
"""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mounts_v5 import profiles  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/mount-phase1-outline.png'
TITLES = {'L': 'Left (H05·H01 / SO1·SO2)', 'REAR': 'Rear (H02 / SO3)', 'FRONT': 'Front (H03 / SO6)', 'R': 'Right (H04·H06 / SO4·SO5)'}


def fill(ax, shape, **style):
    shapes = shape.geoms if hasattr(shape, 'geoms') else [shape]
    for s in shapes:
        if s.is_empty:
            continue
        ax.fill(*s.exterior.xy, **style)
        for hole in s.interiors:
            ax.fill(*hole.xy, color='white', zorder=style.get('zorder', 1) + 0.1)


def main():
    plan = profiles()
    fig, axes = plt.subplots(1, 4, figsize=(16, 7), gridspec_kw=dict(width_ratios=[32, 14, 70, 44]))
    for ax, suffix in zip(axes, ('L', 'REAR', 'FRONT', 'R')):
        p = plan[suffix]
        fill(ax, p['outline'], color='#d9d9d9', zorder=1)
        for pad in p['pads']:
            fill(ax, pad, color='#7a7a7a', zorder=2)
        for hit in p['clearances'].values():
            fill(ax, hit, color='#b0b0b0', zorder=3)
        if p['shim'] is not None:
            fill(ax, p['shim'], color='#9a9a9a', zorder=2)
        for land in p['lands'].values():
            ax.plot(*land.exterior.xy, color='#c0392b', lw=0.8, zorder=4)
        for shape in list(p['hexes'].values()) + list(p['heads'].values()):
            fill(ax, shape, color='#f4d7a8', zorder=4)
        for shape in list(p['bores'].values()) + list(p['slots'].values()):
            fill(ax, shape, color='white', zorder=5)
            ax.plot(*shape.exterior.xy, color='#333333', lw=0.6, zorder=5)
        for key, pocket in p['reliefs'].items():
            fill(ax, pocket.intersection(p['outline']), color='#a9cce3', zorder=4)
            ax.annotate(str(key), pocket.centroid.coords[0], fontsize=7, ha='center', va='center', zorder=6)
        if p['nut'] is not None:
            fill(ax, p['nut'], color='white', zorder=5)
        x0, y0, x1, y1 = p['outline'].bounds
        ax.set_xlim(x0 - 2, x1 + 2)
        ax.set_ylim(y0 - 2, y1 + 2)
        ax.set_aspect('equal')
        ax.set_title(TITLES[suffix], fontsize=9)
        ax.tick_params(labelsize=7)
        ax.grid(True, lw=0.3, alpha=0.5)
    fig.suptitle('46es v5 mounts: outline and plate pads from the CADCraft drawing (grey), hex pockets and head recesses '
                 '(tan), through holes (white), pin reliefs (blue, key numbers), AF 8.5 lands (red)', fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print(OUT)


if __name__ == '__main__':
    main()
