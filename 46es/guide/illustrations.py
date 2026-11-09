"""Orthographic assembly drawings from the same world-coordinate STLs as the 3D viewer."""
import json
import struct
from functools import lru_cache

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
import numpy as np


@lru_cache(maxsize=64)
def triangles(path):
    raw = path.read_bytes()
    count = struct.unpack_from('<I', raw, 80)[0]
    dtype = np.dtype([('normal', '<f4', 3), ('verts', '<f4', (3, 3)), ('tag', '<u2')])
    if not count or len(raw) != 84 + count * dtype.itemsize:
        raise ValueError(f'Invalid binary STL: {path}')
    return np.frombuffer(raw, dtype=dtype, count=count, offset=84)


def selected_meshes(parts, step):
    for part in parts:
        if part['id'] not in step['show']:
            continue
        for piece in part.get('pieces', []):
            stages = step.get('hardwareStages')
            names = piece['bodies']
            if stages is not None and any(n.startswith('REF_M2_') for n in names):
                if not any(n.startswith(s) for n in names for s in stages):
                    continue
            yield part, piece


def draw(out, dest, items, view='iso', arrows=(), size=(8, 3.5), bounds=None):
    camera = np.array({'iso': (.25, -.85, .85), 'front': (0, -1, .015),
                       'top': (0, -.001, 1), 'bottom': (0, -.001, -1)}.get(view, (.25, -.85, .85)))
    camera /= np.linalg.norm(camera)
    right = np.cross((0, 0, 1), camera)
    right /= np.linalg.norm(right)
    up = np.cross(camera, right)
    basis = np.array([right, up, camera]).T
    projected, colors, priority = [], [], []
    for piece, color, focus, lift in items:
        mesh = triangles(out / piece['mesh'])
        normals = mesh['normal']
        visible = normals @ camera > 1e-6
        coords = mesh['verts'][visible] + (0, 0, lift)
        projected.append(coords @ basis)
        light = np.clip(normals[visible] @ np.array([.27, -.41, .87]), -.65, 1)
        rgb = np.array(to_rgb(color))
        colors.append(np.clip(rgb * (.8 + .19 * light[:, None]) + .07, 0, 1))
        priority.append(np.full(len(coords), focus))
    faces = np.concatenate(projected)
    color = np.concatenate(colors)
    depth = faces[:, :, 2].mean(axis=1)
    order = np.lexsort((depth, np.concatenate(priority)))
    fig = plt.figure(figsize=size, dpi=145, facecolor='#f5f6f3')
    ax = fig.add_axes([0, 0, 1, 1], aspect='equal')
    ax.set_axis_off()
    ax.add_collection(PolyCollection(faces[order, :, :2], facecolors=color[order],
                                    edgecolors='face', linewidths=.2))
    marks = []
    for arrow in arrows:
        a, b = np.array([arrow['from'], arrow['to']]) @ basis
        marks.extend([a[:2], b[:2]])
        ax.annotate('', xy=b[:2], xytext=a[:2], arrowprops=dict(
            arrowstyle='-|>', color='#934607', linewidth=2.4, mutation_scale=17))
    points = faces[:, :, :2].reshape(-1, 2)
    if bounds is not None:
        points = (np.array(bounds) @ basis)[:, :2]
    elif marks:
        points = np.vstack([points, marks])
    lo, hi = points.min(axis=0), points.max(axis=0)
    margin = max(float(np.max(hi - lo)) * .055, .5)
    ax.set_xlim(lo[0] - margin, hi[0] + margin)
    ax.set_ylim(lo[1] - margin, hi[1] + margin)
    fig.savefig(out / dest)
    plt.close(fig)


def prepare(out, data):
    folder = out / 'img' / 'build'
    folder.mkdir(parents=True, exist_ok=True)
    for i, part in enumerate(data['parts']):
        if not part.get('pieces'):
            continue
        part['illustration'] = f'img/build/part-{i:02}.png'
        pieces = part['pieces']
        draw(out, part['illustration'],
             [(p, p['color'] if part.get('preserveColors') else '#587d78', False, 0) for p in pieces],
             'bottom' if part.get('preserveColors') else 'iso', size=(1.5, .9))
    for step in data['steps']:
        step['illustration'] = f"img/build/{step['id']}.png"
        items = []
        for part, piece in selected_meshes(data['parts'], step):
            focus = part['id'] in step['focus']
            color = piece['color'] if part.get('preserveColors') else ('#e5953e' if focus else '#d2d9d6')
            items.append((part['id'], piece, color, focus))
        lift = step.get('illustrationLift', {})
        if lift:
            step['installedIllustration'] = f"img/build/{step['id']}-installed.png"
            draw(out, step['installedIllustration'], [(p, c, f, 0) for _, p, c, f in items], step['view'])
        draw(out, step['illustration'], [(p, c, f, lift.get(pid, 0)) for pid, p, c, f in items],
             step['view'], step.get('placement', []))
    r2 = json.loads((out / 'r2-reference.json').read_text(encoding='utf-8'))
    bounds = [(x, y, z) for x in (-8, 293) for y in (-6, 100) for z in (0, 59)]
    for scope in ('all', 'plate', 'cover'):
        old = [p for p in r2['parts'] if scope == 'all' or p['id'] in
               ({'P2', 'P3'} if scope == 'plate' else {'P4', 'P5'})]
        prefixes = {'all': ('PLATE_', 'COVER_', 'MOUNT_', 'CTRL_BRACKET'),
                    'plate': ('PLATE_',), 'cover': ('COVER_',)}[scope]
        current = [p for p in data['parts'] if p['id'].startswith(prefixes)]
        for name, parts in [('r2', old), ('v5', current)]:
            items = []
            for p in parts:
                rank = p.get('explode_rank', 5 if p['id'].startswith('COVER_') else
                             2 if p['id'].startswith('PLATE_') else 0)
                lift = rank * 7 if scope == 'all' else 0
                items.extend((piece, p['color'], False, lift) for piece in p['pieces'])
            draw(out, f'img/build/{name}-{scope}.png', items, bounds=bounds)
    triangles.cache_clear()
