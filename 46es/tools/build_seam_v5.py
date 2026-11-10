"""Build the v5 production CAD from the v5 base timeline (model/seam_v5_base.json).

The r2 cover layers have flat faces. Keep the raised v5 Z 19 top, existing
three-piece outline, keycap clearance, and magnet seats, with one flat face
per piece. The four mounts are extruded directly from the CADCraft drawing
(tools/mounts_v5.py) and the Pro Micro bracket comes from tools/ctrl_v5.py (screwless
snap, no gate). Three separate rest blocks stand on the PSD60 rear-wall bosses under the rear plate flanges
(REAR_RESTS; the plates themselves carry no foot). The front seam of the plate halves (half-lap tab, M2, nut pocket)
and the order-1 seam coupons come from tools/seam_v5.py. The base holds the
plates; its reference-only switch envelopes and Wilmore housing stay suppressed (the review
model re-enables the housing). The three cover pieces (tools/cover_v5.py), the seam spine (tools/spine_v5.py) and
the reference screws, nuts and magnets (tools/hardware_v5.py) are code since 2026-11-10 and run after the base.

model/seam_v5_base.json is source, one parameter or feature per line. It was cut from the v4 document on 2026-11-10
(suppressed v4 mount/bracket chains, orphan sketches and dimensions dropped, the fixed v5 edits folded in, every
body's BRep unchanged); the v4 file is in git history (tag 46es-pre-cleanup-2026-11-09 and earlier). Parts of it
move into generator code step by step when the shape stays identical (plan 4-5): covers, spine and reference
hardware, and since the 2026-11-10 seam redesign the front seam and its coupons; the plate bodies themselves stay
(their outlines and openings are the r2 drawing's sketches).

Outputs: model/46es_mount_seam_v5.sc (production), model/ctrl_trials_v5.sc (order-1 snap trials A/C, rear rest
height variants and seam coupons),
model/parameters_seam_v5.csv (production parameters) and model/seam_v5_build.json (build record).
Run from the repository root with python 46es/tools/build_seam_v5.py.
  --probe   build into .cache/v5 without replacing the current CAD
  --mounts  build only the four mounts into .cache/v5/mounts_v5.sc from a
            parameter-only document and check their sections (seconds, for mount iteration)
  --ctrl    build only the brackets B, A, C into .cache/v5/ctrl_v5.sc and check volumes and keep-outs
  --covers  build only the three cover pieces into .cache/v5/covers_v5.sc, check them and compare with production
  --refresh-record  after an edit that must not change the model: probe-build, require the
            committed CAD's document and bodies to be reproduced exactly, update only
            model/seam_v5_build.json (the CAD bytes, and every record tied to them, stay)
"""
# SOURCE OF TRUTH - Edit this file. Do NOT hand-edit generated .sc files.
# Regenerate outputs with: python tools/build_seam_v5.py (and export scripts as needed)
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

from make_key_dxf import load_keys, rect
from mounts_v5 import (MOUNTS, LEFT_MOUNT, RIGHT_MOUNT, REAR_MOUNT, FRONT_MOUNT, PLATE_SUPPORT_MOUNTS,  # noqa: F401
                       MX_GUIDES, MX_CONTACTS, MX_CONTACT_SIZE, MX_PIN_DEPTH_FROM_SEAT, MOUNT_PIN_CLEARANCE,
                       PAD_ROOT_Z, PAD_TOP_Z, SHIM_TOP_Z, SO_ANCHORS, PLATE_FLANGE_INNER, SEAM_NUT_CLEARANCE,
                       profiles as mount_profiles, expected_sections, expected_volume, emit as emit_mounts)
import ctrl_v5
import cover_v5
import hardware_v5
import seam_v5
import spine_v5
from cad_eval_cache import seed as seed_evaluation
from export_print_v5 import prebuild, seal_prebuilt
from common import ROOT, CLI, sha, fingerprints, write_json

BASE = ROOT / 'model/seam_v5_base.json'
OUTPUT = ROOT / 'model/46es_mount_seam_v5.sc'
# Order-1 snap trial brackets A/C (tools/ctrl_v5.py TRIALS): free bodies without plate cuts, so they live in a small
# parameter-only model of their own (plan 3-3, user 2026-11-10) instead of the production timeline.
TRIALS_OUTPUT = ROOT / 'model/ctrl_trials_v5.sc'
PARAMETERS_CSV = ROOT / 'model/parameters_seam_v5.csv'
CACHE = ROOT / '.cache/v5'          # build scratch (seeds, pending models, reports); not tracked
MOUNTS_ONLY = CACHE / 'mounts_v5.sc'
CTRL_ONLY = CACHE / 'ctrl_v5.sc'
COVERS_ONLY = CACHE / 'covers_v5.sc'
KEY_MARGIN = 1.0
LEGMAG_SKIN_MIN = 1.3
CAP_1U = 18.05
SEAT_ROOT_Z = PAD_ROOT_Z
# Leg-end magnet pairs (lower legs only, user 2026-11-06). Chosen on a 0.05 mm raster so that
# cover pocket Ø3.2 and plate pocket Ø3.3 keep >= 1.2 mm to the v5 window, the 16.5 openings
# and the part edges, as close to the leg tip as that allows.
LEG_MAGNETS = {'L': (94.0, 2.5, 'PLATE_L_SPLIT_V1', 'COVER_L_DRAFT_TBD'),
               'R': (167.7, 2.5, 'PLATE_R_SPLIT_V1', 'COVER_R_DRAFT_TBD')}
LEGMAG_POCKET_R = 1.6                # cover pocket (TBD_magnet_D 3 + 2 × TBD_magnet_clr 0.1) / 2
LEGMAG_WINDOW_WALL = 1.15            # pocket wall to the cover window (per-key window: L 1.184, R 1.171; rule >= 1.0)
COVERS = ['COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD']
# PSD60 Defender rear-wall bosses (user photo, KPrepublic product image, 2026-11-09): four half-round bosses without
# a hole on the inner rear wall. Centres X are photo estimates (perspective fitted on H01-H06, residual <= 0.8 mm,
# leave-one-out spread 2-4 mm), diameter about 8-10. Top assumed at the support top Z 0: r2's bottom ring P0
# (2T, 4 mm border, M2 holes on H01/H05/H06) crossed them without notches. Not measured.
REAR_BOSS_X = (36.0, 113.6, 170.1, 245.8)
REAR_BOSS_D = 9.0
REAR_BOSS_TOP_Z = 0.0
# Bosses 1-3 lie under the rear plate flanges. A separate rest block stands on each (stuck to the boss top with the
# pad that fills REAR_REST_GAP) and the flange bottom sits on the block. Until 2026-11-10 the block was a foot joined
# to the plate; it made the plate print 12.5 mm tall with three thin fins and need support (user 2026-11-10), so the
# plate lost it. Boss 4 sits under the right mount's rear corner beside SO4, where the flange is interrupted: no rest.
REAR_RESTS = {1: (37.0, 'PLATE_L_SPLIT_V1'), 2: (113.0, 'PLATE_L_SPLIT_V1'), 3: (170.0, 'PLATE_R_SPLIT_V1')}
REAR_REST_BODY = 'REAR_REST_{}_V5'
REAR_REST_L = 14.0                 # along X, as the former foot
REAR_REST_W = 4.0                  # along Y from the rear plate edge: the 2 mm flange plus 2 mm towards the boss front
REAR_REST_GAP = 0.5                # block bottom above the boss top: the adhesive pad
REAR_FLANGE_BOTTOM_Z = 5.0         # plate_top_Z - TBD_plate_T - split_flange_H (checked after evaluation)
REAR_REST_H = REAR_FLANGE_BOTTOM_Z - REAR_BOSS_TOP_Z - REAR_REST_GAP
REAR_REST_CHORD_MARGIN = 2.0       # the boss chord under the flange stays under the block for this photo error (each side)
REAR_REST_COLOR = [226, 172, 60]
# Order-1 height variants (model/ctrl_trials_v5.sc): the boss top height is an assumption and MJF is +-0.3, so the
# block that leaves room for the pad without lifting the plate off the standoffs is picked at trial assembly.
REAR_REST_TRIALS = {'REAR_REST_TRIAL_LO': dict(dh=-0.3, origin=(156.0, -50.0)),
                    'REAR_REST_TRIAL_HI': dict(dh=0.3, origin=(156.0, -42.0))}
REAR_FLANGES = ('PLATE_FLANGE_L_REAR', 'PLATE_FLANGE_R_REAR_A', 'PLATE_FLANGE_R_REAR_B')
PLATE_REAR_Y = 94.967              # rear plate edge (flange outer face), as in the base flange features
# Reference-only solids of the base, suppressed in production. The review model
# (tools/build_assembly_reference_v5.py) re-enables the housing features with measured PSD60 values.
REFERENCE_FEATURES = ('HOUSING_OUTER_REF_WIL', 'HOUSING_CAVITY_TBD', 'HOUSING_POSTS_CAND', 'HOUSING_USB_CUT_TBD',
                      'REF_SWITCH_LOWER_PINS_BOUND_ASSUMED', 'REF_SWITCH_LATCH_BOUND_ASSUMED',
                      'REF_SWITCH_UPPER_BOUND_ASSUMED')


# ------------------------------------------------------------------------------------ build record
# Everything the production CAD is generated from. check_repository.py recomputes these fingerprints and the
# output hash, so a commit that changes an input without regenerating the CAD (or the reverse) fails CI.
BUILD_INPUTS = ('tools/build_seam_v5.py', 'tools/mounts_v5.py', 'tools/ctrl_v5.py', 'tools/cover_v5.py',
                'tools/spine_v5.py', 'tools/hardware_v5.py', 'tools/seam_v5.py', 'tools/make_key_dxf.py',
                'model/mounts_cadcraft_phase1.dxf', 'inspection/data/features_by_panel.json',
                'firmware/46es_kbfirmware.json', 'model/seam_v5_base.json')
BUILD_RECORD = ROOT / 'model/seam_v5_build.json'


def build_record():
    return dict(generator='tools/build_seam_v5.py', output=OUTPUT.relative_to(ROOT).as_posix(),
                trials_output=TRIALS_OUTPUT.relative_to(ROOT).as_posix(),
                inputs=fingerprints(BUILD_INPUTS))


def stale_reasons():
    """Why the committed CAD does not match its build record (empty when it does)."""
    if not BUILD_RECORD.is_file():
        return ['missing build record']
    recorded, current = json.loads(BUILD_RECORD.read_text(encoding='utf-8')), build_record()
    reasons = [f'input changed: {rel}' for rel in sorted(set(recorded['inputs']) | set(current['inputs']))
               if recorded['inputs'].get(rel) != current['inputs'].get(rel)]
    for key, path in (('output', OUTPUT), ('trials_output', TRIALS_OUTPUT)):
        if recorded.get(key) != current[key] or not path.is_file() or sha(path) != recorded.get(key + '_sha'):
            reasons.append(f'{current[key]} differs from its build record')
    return reasons


def write_build_record():
    record = build_record()
    record['output_sha'] = sha(OUTPUT)
    record['trials_output_sha'] = sha(TRIALS_OUTPUT)
    write_json(BUILD_RECORD, record, sort_keys=True)


def run(*args):
    result = subprocess.run([str(CLI), *map(str, args)], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace')[-5000:])


def overlap(a, b):
    """Separating-axis test for two convex polygons."""
    for poly in (a, b):
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = y1 - y2, x2 - x1
            pa = [nx * x + ny * y for x, y in a]
            pb = [nx * x + ny * y for x, y in b]
            if max(pa) <= min(pb) + 1e-9 or max(pb) <= min(pa) + 1e-9:
                return False
    return True


def key_rects(keys, m):
    """Keycap footprints (actual widths) grown by m on every side."""
    return [rect(k['x'], k['y'], CAP_1U + (k['w_u'] - 1) * 19.05 + 2 * m, CAP_1U + 2 * m, k['rot']) for k in keys]


def margin_groups(keys, m=KEY_MARGIN):
    """Grown keycap rectangles, split into groups whose members do not overlap (one sketch each)."""
    groups = []
    for r in key_rects(keys, m):
        for g in groups:
            if not any(overlap(r, o) for o in g):
                g.append(r)
                break
        else:
            groups.append([r])
    return groups


# ------------------------------------------------------------------------------------ BRep top-level audit
def horizontal_faces(solid):
    """(z, signed plan area) of every horizontal planar face of a cached SolidCraft solid; +area = normal +Z.

    The cache stores loops clockwise when seen along the outward normal, so the shoelace sum is negated.
    """
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from read_sc_cache import curve_points
    out = []
    for shell in solid['shells']:
        for face in shell['faces']:
            sf = face['surface']
            if sf['kind'] != 'plane_through':
                continue
            a, u, v = sf['origin'], sf['u_point'], sf['v_point']
            if abs(u[2] - a[2]) + abs(v[2] - a[2]) > 5e-5:
                continue
            area = 0.0
            for loop in face['loops']:
                for edge in loop:
                    pts = curve_points(shell['edges'][edge['edge']]['curve'])
                    if not edge['forward']:
                        pts = pts[::-1]
                    area += sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:])) / 2
            out.append((a[2], -area))
    return out


def top_levels(model, bodies=COVERS, tol=1e-4):
    """Per body: {Z: area} of the upward (+Z) horizontal faces, Z rounded to 1e-4."""
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from cad_model import live_shapes
    shapes = live_shapes(model)
    levels = {}
    for name in bodies:
        acc = {}
        for solid in shapes[name]:
            for z, area in horizontal_faces(solid):
                if area > tol:
                    key = round(z, 4)
                    acc[key] = acc.get(key, 0.0) + area
        levels[name] = {z: round(a, 3) for z, a in sorted(acc.items())}
    return levels


# ------------------------------------------------------------------------------------ document helpers
def silhouette_polys(keys, cell, close_r, min_rail, edge, res=0.1, fill_L=0.0, width='env_u'):
    """키 블록 실루엣 창. make_key_dxf.py::silhouette_polys와 동일 로직(width='env_u'). width='w_u'면 r2 칸 대신 실제 키캡 폭."""
    import numpy as np
    from scipy import ndimage

    cell_val = float(cell)
    close_r_val = float(close_r)
    min_rail_val = float(min_rail)
    res_val = float(res)
    fill_L_val = float(fill_L)

    x0, x1, y0, y1 = edge
    xs = np.arange(x0 - 2, x1 + 2, res_val)
    ys = np.arange(y0 - 2, y1 + 2, res_val)
    blocks = [[k for k in keys if k["rot"] < 0], [k for k in keys if k["rot"] >= 0]]
    r = close_r_val / res_val

    def closing(B):
        p = int(r) + 2
        Bp = np.pad(B, p)
        D = ndimage.distance_transform_edt(~Bp) <= r
        E = ndimage.distance_transform_edt(D) > r
        return E[p:-p, p:-p]

    def seg_closing(B):
        if fill_L_val <= 0:
            return B
        n = int(round(fill_L_val / res_val)) | 1
        p = n + 2
        Bp = np.pad(B, p)
        C = ndimage.binary_closing(Bp, np.ones((1, n), bool)) | ndimage.binary_closing(Bp, np.ones((n, 1), bool))
        return C[p:-p, p:-p]

    def _raster_cells(block_keys, cell_size, xs_arr, ys_arr, res_val):
        U = np.zeros((len(ys_arr), len(xs_arr)), dtype=bool)
        for k in block_keys:
            w = k[width] * 19.05 - (19.05 - cell_size)
            pts = rect(k["x"], k["y"], w, cell_size, k["rot"])
            n = len(pts)
            area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
            sgn = 1 if area > 0 else -1
            jx0 = max(0, int((min(p[0] for p in pts) - xs_arr[0]) / res_val) - 1)
            jx1 = min(len(xs_arr), int((max(p[0] for p in pts) - xs_arr[0]) / res_val) + 2)
            iy0 = max(0, int((min(p[1] for p in pts) - ys_arr[0]) / res_val) - 1)
            iy1 = min(len(ys_arr), int((max(p[1] for p in pts) - ys_arr[0]) / res_val) + 2)
            Xs, Ys = np.meshgrid(xs_arr[jx0:jx1], ys_arr[iy0:iy1])
            m = np.ones(Xs.shape, dtype=bool)
            for i in range(n):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
                m &= sgn * ((bx - ax) * (Ys - ay) - (by - ay) * (Xs - ax)) >= 0
            U[iy0:iy1, jx0:jx1] |= m
        return U

    U = np.zeros((len(ys), len(xs)), dtype=bool)
    for block in blocks:
        Ub = closing(seg_closing(_raster_cells(block, cell_val, xs, ys, res_val)))
        Ub = ndimage.binary_fill_holes(Ub)
        U |= Ub
    X, Y = np.meshgrid(xs, ys)
    U &= (X >= x0 + min_rail_val) & (X <= x1 - min_rail_val) & (Y >= y0 + min_rail_val) & (Y <= y1 - min_rail_val)
    labels, n = ndimage.label(U)
    polys = []
    for lab in range(1, n + 1):
        M = labels == lab
        if M.sum() * res_val * res_val < 50:
            continue
        polys.append(_trace_boundary(M, xs, ys, res_val, tol=0.15))
    return polys, U, res_val


def _trace_boundary(M, xs, ys, res, tol):
    import numpy as np
    H, W = M.shape
    P = np.zeros((H + 2, W + 2), dtype=bool)
    P[1:-1, 1:-1] = M
    edges = {}

    def add(a, b):
        edges.setdefault(a, []).append(b)
        edges.setdefault(b, []).append(a)

    dv = P[1:, :] != P[:-1, :]
    for i, j in zip(*np.nonzero(dv)):
        add((i + 1, j), (i + 1, j + 1))
    dh = P[:, 1:] != P[:, :-1]
    for i, j in zip(*np.nonzero(dh)):
        add((i, j + 1), (i + 1, j + 1))
    seen = set()
    best = []
    for start in edges:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = None, start
        while True:
            nbrs = [p for p in edges[cur] if p != prev]
            if not nbrs:
                break
            nxt = nbrs[0]
            if nxt == start:
                break
            loop.append(nxt)
            seen.add(nxt)
            prev, cur = cur, nxt
        if len(loop) > len(best):
            best = loop
    pts = [(xs[0] - res / 2 + (j - 1) * res, ys[0] - res / 2 + (i - 1) * res) for i, j in best]
    return _dp(pts, tol)


def _dp(pts, tol):
    import math

    def dp_open(p):
        if len(p) < 3:
            return p
        (ax, ay), (bx, by) = p[0], p[-1]
        L = math.hypot(bx - ax, by - ay) or 1e-9
        dmax, idx = 0, 0
        for i in range(1, len(p) - 1):
            d = abs((bx - ax) * (ay - p[i][1]) - (ax - p[i][0]) * (by - ay)) / L
            if d > dmax:
                dmax, idx = d, i
        if dmax > tol:
            return dp_open(p[:idx + 1])[:-1] + dp_open(p[idx:])
        return [p[0], p[-1]]

    n = len(pts)
    i0 = 0
    i1 = max(range(n), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    a = dp_open(pts[i0:i1 + 1])
    b = dp_open(pts[i1:] + pts[:1])
    out = a[:-1] + b[:-1]
    return out


# Cover window (2026-11-09): one silhouette outline per key block instead of per-key margin rectangles.
# cell 20.35 = keycap 18.05 + 2 × KEY_MARGIN 1.0 + 0.3 for the 0.1 raster and the 0.15 outline simplification, so the
# window still holds every keycap + 1.0 (the trial value 16 left 0.31, user 2026-11-10). min_rail 1.1: keys 9, 31 and
# 40 come within 1.16 of the cover edge (the per-key window already left that rail; resin wall limit 1.0).
# Cells use the keycap width w_u, not the r2 slot env_u: with env_u the 1.5u slot of key 19 carried the window to
# the right edge and cut the cover lip into a 0.28 mm sliver.
COVER_SILHOUETTE = dict(cell=20.35, close_r=0.0, fill_L=16.0, min_rail=1.1, res=0.1)
COVER_EDGE_GAP = 0.3                       # case inner W 286.381 × D 95.934, PCB origin offset (0.693, 0.667)


def cover_windows():
    """cover_window_cuts() cached under a hash of everything it reads (plan 3-8: the raster takes about 4.5 s).

    The key covers the key layout, the window and magnet constants, the source of every function the result
    comes from and the numpy/scipy/shapely versions, so any change to them recomputes."""
    import hashlib
    import inspect
    import numpy, scipy, shapely
    import make_key_dxf
    sources = [inspect.getsource(f) for f in (cover_window_cuts, silhouette_polys, _trace_boundary, _dp, key_rects,
                                              overlap, make_key_dxf.rect, make_key_dxf.load_keys)]
    key_data = dict(keys=load_keys(.693, .667), silhouette=COVER_SILHOUETTE, edge_gap=COVER_EDGE_GAP,
                    magnets=LEG_MAGNETS, pocket_r=LEGMAG_POCKET_R, window_wall=LEGMAG_WINDOW_WALL, margin=KEY_MARGIN,
                    cap=CAP_1U, sources=sources, versions=[numpy.__version__, scipy.__version__, shapely.__version__])
    digest = hashlib.sha256(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()[:16]
    cached = CACHE / 'prep' / f'cover_windows_{digest}.json'
    if cached.is_file():
        return [[tuple(p) for p in poly] for poly in json.loads(cached.read_text(encoding='utf-8'))]
    polys = cover_window_cuts()
    cached.parent.mkdir(parents=True, exist_ok=True)
    write_json(cached, polys, indent=None)
    return polys


def cover_window_cuts():
    """Plan polygons of the cover window cuts (GH60 PCB coordinates)."""
    in_w, in_d, gap = 286.381, 95.934, COVER_EDGE_GAP
    edge = (-.693 + gap, in_w - .693 - gap, -.667 + gap, in_d - .667 - gap)
    s = COVER_SILHOUETTE
    keys = load_keys(.693, .667)
    polys, _, _ = silhouette_polys(keys, cell=s['cell'], close_r=s['close_r'], min_rail=s['min_rail'],
                                   edge=edge, res=s['res'], fill_L=s['fill_L'], width='w_u')
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
    # The leg magnets were placed against the per-key window (wall 1.17-1.18); the silhouette's 0.15 oversize came within 0.98
    # of the L pocket. Moving the magnet would move the plate pocket, so the window keeps clear of both pockets.
    keep = unary_union([Point(x, y).buffer(LEGMAG_POCKET_R + LEGMAG_WINDOW_WALL, quad_segs=8)
                        for x, y, _, _ in LEG_MAGNETS.values()])
    shapes = [Polygon(p).buffer(0).difference(keep) for p in polys]
    polys = [[(round(x, 4), round(y, 4)) for x, y in g.exterior.coords[:-1]]
             for s in shapes for g in getattr(s, 'geoms', [s])]
    window = unary_union([Polygon(p) for p in polys])
    assert not window.intersects(keep.buffer(-1e-3))
    short = [i for i, r in enumerate(key_rects(keys, KEY_MARGIN), 1) if not window.covers(Polygon(r))]
    assert not short, f'cover window misses keycap + {KEY_MARGIN} at keys {short}'
    return polys


def read_source():
    """The base document and its container record; every feature other than REFERENCE_FEATURES evaluates."""
    base = json.loads(BASE.read_text(encoding='utf-8'))
    doc = base['document']
    off = sorted(f['name'] for f in doc['features'] if f['suppressed'])
    assert off == sorted(REFERENCE_FEATURES), off
    return doc, json.dumps(base['container'], separators=(',', ':'))


def helpers(doc):
    """feature()/sketch() closures that append native timeline features to doc."""
    def feature(kind, name, **kwargs):
        fid = doc['next_id']; doc['next_id'] += 1
        doc['features'].append(dict(id=fid, type=kind, name=name, suppressed=False, **kwargs))
        return fid

    def sketch(name, plane, polygons):
        points = [dict(id='origin', pos=[0., 0.], fixed=True)]
        curves = []
        for poly in polygons:
            first = len(points)
            for x, y in poly:
                points.append(dict(id=f'p{len(points)}', pos=[float(x), float(y)], fixed=True))
            for j in range(len(poly)):
                curves.append(dict(id=f'l{len(curves) + 1}', type='line', construction=False,
                                   a=first + j, b=first + (j + 1) % len(poly)))
        return feature('sketch', name, plane=plane,
                       sketch=dict(points=points, curves=curves, constraints=[],
                                   counters=dict(p=len(points), l=len(curves))))

    return feature, sketch


def write_seed(doc, container, path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('document.json', json.dumps(doc, ensure_ascii=False))
        archive.writestr('container.json', container)


def evaluate(seed, pending, after=()):
    """Evaluate the seed, save it as `pending` and measure it in one CLI call (plan 3-1: a separate run --save
    and eval opened and evaluated the model twice). file.save_as names the document after the file stem, as
    run --save did. `after` runs in the same call once saved (plan 3-6: parameter CSV, print exports), so they need
    no model load of their own. Returns the measurement and the wall time of the call."""
    started = time.perf_counter()
    script = pending.with_name(f'save_{pending.stem}.json')
    write_json(script, [dict(command='file.save_as', params=dict(path=str(pending))), *after], indent=None)
    report = pending.with_name(f'eval_{pending.stem}.json')
    run('eval', script, '--in', seed, '--json-out', report)
    elapsed = time.perf_counter() - started
    evaluated = json.loads(report.read_text(encoding='utf-8'))
    failed = [f for f in evaluated['timeline'] if f.get('error')]
    assert not failed, failed
    seed_evaluation(pending, report)      # later stages read it by the saved bytes (cad_eval_cache)
    return evaluated, elapsed


def check_mounts(evaluated, mounts):
    """Every mount is one closed body whose volume and box follow the drawing and the parameters."""
    bodies = {b['name']: b for b in evaluated['bodies']}
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    for name, (_, anchor, _) in SO_ANCHORS.items():
        index = name[2]
        evaluated_anchor = (values[f'REF_SO_dX{index}'] - values['TBD_pcb0_dx'], values[f'REF_SO_dY{index}'] - values['TBD_pcb0_dy'])
        assert all(abs(a - b) < 1e-6 for a, b in zip(anchor, evaluated_anchor)), (name, anchor, evaluated_anchor)
    assert abs(values['plate_top_Z'] - values['TBD_plate_T'] - PAD_TOP_Z) < 1e-9
    assert abs(values['split_spine_bottom_Z'] - values['split_support_gap'] - SHIM_TOP_Z) < 1e-9
    assert abs(values['split_flange_W'] - 2.0) < 1e-9 and abs(values['split_flange_H'] - 3.0) < 1e-9
    assert abs(-values['TBD_pcb0_dx'] + values['TBD_plate_gap'] + values['split_flange_W'] - PLATE_FLANGE_INNER[0]) < 1e-9
    report = {}
    for suffix, profile in mounts.items():
        body = bodies[profile['mount']]
        expected = expected_volume(profile)
        x0, y0, x1, y1 = profile['outline'].bounds
        box_ok = all(abs(a - b) < 0.01 for a, b in zip(body['bbox']['min'][:2] + body['bbox']['max'][:2], (x0, y0, x1, y1)))
        top = PAD_TOP_Z if profile['pads'] else values['TBD_frame_T']
        assert body['closed'] and box_ok and abs(body['bbox']['min'][2]) < 1e-6 and abs(body['bbox']['max'][2] - top) < 1e-6, body
        assert abs(body['volume_mm3'] - expected) / expected < 0.002, (profile['mount'], body['volume_mm3'], expected)
        report[profile['mount']] = dict(volume_mm3=round(body['volume_mm3'], 3), expected_mm3=round(expected, 3),
                                        bbox=body['bbox'])
    return report


def rear_rest_plan(doc):
    """Rest block X spans under the rear flanges, how much photo error each boss estimate tolerates and the bearing
    area of each block on its boss.

    The flange spans come from the base flange features themselves, so a moved flange fails here instead of
    leaving a block without a flange above it."""
    from shapely.geometry import Point, box as rect_box
    flanges = {}
    for f in doc['features']:
        if f.get('name') in REAR_FLANGES and not f.get('suppressed'):
            x0 = float(f['corner'][0])
            assert f['corner'][1] == f'{PLATE_REAR_Y} - split_flange_W', f['corner']
            flanges.setdefault(f['participants'][0], []).append((x0, x0 + float(f['length'])))
    assert sum(len(v) for v in flanges.values()) == len(REAR_FLANGES), flanges
    params = {p['name']: p['expr'] for p in doc['params']}
    assert params['split_flange_W'] == '2 mm', params['split_flange_W']
    wall_y = 95.934 - 0.667                     # TBD_case_in_D - TBD_pcb0_dy (Wilmore stand-in, checked after eval)
    inner_y = PLATE_REAR_Y - 2.0
    assert REAR_REST_W >= 2.0 and PLATE_REAR_Y < wall_y
    r = REAR_BOSS_D / 2
    chord = (r * r - (wall_y - inner_y) ** 2) ** 0.5   # half width of the boss top at the flange inner face
    plan = {}
    for i, (x, plate) in REAR_RESTS.items():
        x0, x1 = x - REAR_REST_L / 2, x + REAR_REST_L / 2
        assert any(a <= x0 and x1 <= b for a, b in flanges[plate]), (i, x0, x1, flanges[plate])
        boss = REAR_BOSS_X[i - 1]
        margin = (round(boss - chord - x0, 3), round(x1 - boss - chord, 3))
        assert min(margin) >= REAR_REST_CHORD_MARGIN, (i, margin)
        block = rect_box(x0, PLATE_REAR_Y - REAR_REST_W, x1, PLATE_REAR_Y)
        bearing = [block.intersection(Point(boss + dx, wall_y).buffer(r, quad_segs=32)).area
                   for dx in (0.0, -REAR_REST_CHORD_MARGIN, REAR_REST_CHORD_MARGIN)]
        plan[i] = dict(plate=plate, body=REAR_REST_BODY.format(i), rest_X=[x0, x1],
                       rest_Y=[round(PLATE_REAR_Y - REAR_REST_W, 3), PLATE_REAR_Y], boss_X=boss,
                       boss_chord_half=round(chord, 3), full_chord_margin_mm=list(margin),
                       bearing_on_boss_mm2=round(bearing[0], 2),
                       bearing_on_boss_min_mm2=round(min(bearing), 2),
                       flange_contact_mm2=round(REAR_REST_L * 2.0, 2))
    boss4 = REAR_BOSS_X[3]
    assert not any(a < boss4 + r and boss4 - r < b for spans in flanges.values() for a, b in spans), 'boss 4 under a flange'
    return plan


def check_rear_rests(evaluated, trials, plan):
    """Each rest block is a closed box from the pad to the flange bottom; the plates end at the flange bottom (no
    foot); the wall line the plan assumed is the evaluated one; the height variants differ only in height."""
    bodies = {b['name']: b for b in evaluated['bodies']}
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    assert abs(values['TBD_case_in_D'] - values['TBD_pcb0_dy'] - (95.934 - 0.667)) < 1e-6
    flange_bottom = values['plate_top_Z'] - values['TBD_plate_T'] - values['split_flange_H']
    assert abs(flange_bottom - REAR_FLANGE_BOTTOM_Z) < 1e-9
    assert abs(values['v5_rear_rest_H'] - REAR_REST_H) < 1e-9, values['v5_rear_rest_H']
    bottom = values['v5_rear_boss_top_Z'] + values['v5_rear_rest_gap']
    for plate in {p['plate'] for p in plan.values()}:
        b = bodies[plate]
        assert b['closed'] and abs(b['bbox']['min'][2] - flange_bottom) < 1e-6, (plate, b['bbox'])
    volume = REAR_REST_L * REAR_REST_W * REAR_REST_H
    for i, p in plan.items():
        b = bodies[p['body']]
        expected = (p['rest_X'][0], p['rest_Y'][0], bottom, p['rest_X'][1], p['rest_Y'][1], flange_bottom)
        assert b['closed'] and all(abs(a - e) < 1e-6 for a, e in zip(b['bbox']['min'] + b['bbox']['max'], expected)), (i, b['bbox'])
        assert abs(b['volume_mm3'] - volume) < 1e-6, (i, b['volume_mm3'])
    variants = {}
    trial_bodies = {b['name']: b for b in trials['bodies']}
    for body, spec in REAR_REST_TRIALS.items():
        b = trial_bodies[body]
        height = REAR_REST_H + spec['dh']
        size = [b['bbox']['max'][k] - b['bbox']['min'][k] for k in range(3)]
        assert b['closed'] and all(abs(a - e) < 1e-6 for a, e in zip(size, (REAR_REST_L, REAR_REST_W, height))), (body, size)
        variants[body] = round(height, 3)
    return dict(rest_Z=[bottom, flange_bottom], rest_volume_mm3=round(volume, 3), height_variants_mm=variants, rests=plan)


def rear_rest_clearance(plan, mounts, bodies, minimum=1.0):
    """Plan-view distance of each rest block to the mounts, the switch bodies and the USB outlet keepout.

    The blocks stand below the plate (Z 0.5-5) where the mount frames (Z 0-3) and the switch housings live."""
    from shapely.geometry import box as rect_box
    from mounts_v5 import switch_pins
    switches = [k['body'] for k in switch_pins()]
    usb = bodies['USB_OUTLET_TBD']['bbox']
    usb_box = rect_box(usb['min'][0], usb['min'][1], usb['max'][0], usb['max'][1])
    out = {}
    for i, p in plan.items():
        block = rect_box(p['rest_X'][0], p['rest_Y'][0], p['rest_X'][1], p['rest_Y'][1])
        d = dict(mount=min(m['outline'].distance(block) for m in mounts.values()),
                 switch_body=min(s.distance(block) for s in switches), usb_outlet=usb_box.distance(block))
        assert min(d.values()) >= minimum, (i, d)
        out[i] = {k: round(v, 3) for k, v in d.items()}
    return out


def seam_coupon_bodies():
    return [body for name in seam_v5.COUPONS for body in seam_v5.coupon_bodies(name)]


def switch_openings():
    """Plan polygons of the 16.5 mm upper switch openings (plate position)."""
    from shapely.geometry import Polygon
    return [Polygon(rect(k['x'], k['y'], 16.5, 16.5, k['rot'])) for k in load_keys(.693, .667)]


def emit_seam(doc, feature, sketch):
    """Front seam on the plate halves, right after the base timeline; its sketches are hidden like the base's."""
    first = doc['next_id']
    seam_v5.emit(feature, sketch)
    doc['visibility']['hidden_sketches'] += [f['id'] for f in doc['features'] if f['id'] >= first and f['type'] == 'sketch']


def check_seam(evaluated, trials):
    """The document's seam_* parameters and plate levels are the numbers tools/seam_v5.py drew; every variant passes
    its wall rules; each coupon piece is one closed body on its side of the seam with the tab reaching over."""
    s, seam = seam_v5, seam_v5.PRODUCTION
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    for name, value in [('seam_tab_T', seam.tab_T), ('seam_M2_X', seam.screw[0]), ('seam_M2_Y', seam.screw[1]),
                        ('seam_cb_D', seam.cb_D), ('seam_nut_D', seam.nut_D), ('plate_top_Z', s.PLATE_TOP_Z),
                        ('split_plate_gap', s.SPLIT_GAP), ('split_M2_clear_D', s.M2_CLEAR_D),
                        ('split_M2_head_D', s.M2_HEAD_D), ('TBD_cover_lip_H', s.COVER_LIP_H),
                        ('v5_seam_fit', seam.fit), ('v5_seam_nut_AF', seam.nut_AF)]:
        assert abs(values[name] - value) < 1e-9, (name, values[name], value)
    assert abs(values['TBD_frame_T'] + values['TBD_standoff_H'] - s.PLATE_BOTTOM_Z) < 1e-9
    assert abs(values['split_center_X'] + values['split_SO_bypass'] - s.SPLIT_FRONT_X) < 1e-9
    assert abs(-values['TBD_pcb0_dy'] + values['TBD_plate_gap'] + values['TBD_cover_wall'] + values['TBD_cover_lip_clr']
               - s.RABBET_INNER_Y) < 1e-9
    assert (seam.screw, s.FRONT_PAD_HOLE_R) == SEAM_NUT_CLEARANCE, SEAM_NUT_CLEARANCE
    openings = switch_openings()
    report = dict(production=s.check(seam, openings), coupons={})
    bodies = {b['name']: b for b in evaluated['bodies']}
    for name in ('PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1', 'REF_M2_SEAM_FRONT', 'REF_M2_SEAM_FRONT_NUT'):
        assert bodies[name]['closed'], name
    assert abs(bodies['PLATE_L_SPLIT_V1']['bbox']['max'][0] - s.TAB_END_X) < 1e-6, bodies['PLATE_L_SPLIT_V1']['bbox']
    trial_bodies = {b['name']: b for b in trials['bodies']}
    x0, y0, x1, y1 = s.COUPON_BOX
    for name, (variant, (dx, dy)) in s.COUPONS.items():
        left, right = (trial_bodies[b] for b in s.coupon_bodies(name))
        tab_end = max(x for x, _ in s.outlines(variant)[0])
        boxes = ((left, (x0 + dx, y0 + dy, s.PLATE_BOTTOM_Z, tab_end + dx, y1 + dy, s.PLATE_TOP_Z)),
                 (right, (s.SPLIT_LINE[2][0] + s.SPLIT_GAP / 2 + dx, y0 + dy, s.PLATE_BOTTOM_Z, x1 + dx, y1 + dy, s.PLATE_TOP_Z)))
        for body, box in boxes:
            assert body['closed'] and all(abs(a - e) < 1e-4 for a, e in zip(body['bbox']['min'] + body['bbox']['max'], box)), \
                (name, body['name'], body['bbox'], box)
        report['coupons'][name] = dict(s.check(variant), volume_mm3=[round(left['volume_mm3'], 3), round(right['volume_mm3'], 3)])
    return report


def emit_rear_rest_trials(feature, doc):
    """The order-1 height variants: free boxes beside the coupons (trials model and review model)."""
    for body, spec in REAR_REST_TRIALS.items():
        x, y = spec['origin']
        feature('box', body, corner=[x, y, 0.0], length=str(REAR_REST_L), width=str(REAR_REST_W),
                height=str(round(REAR_REST_H + spec['dh'], 6)), operation='new_body', body_names=[body])
        doc['appearances']['bodies'][body] = dict(name='Custom', color=REAR_REST_COLOR, opacity=1.0)


def ctrl_params():
    """Documentation parameters for the snap bracket (the sketches are fixed numbers from tools/ctrl_v5.py).

    Every number in the comments comes from ctrl_v5 constants or its bracket report, so a design change
    cannot leave a stale comment behind."""
    c = ctrl_v5
    (x1, y1), (x2, y2) = c.M2_XY
    a, t = c.TRIALS['CTRL_SNAP_TRIAL_A'], c.TRIALS['CTRL_SNAP_TRIAL_C']
    report = c.bracket()['report']
    (cx, _), (cl, _), _ = c.COMPONENTS['CRYSTAL']
    crystal_end = c.PCB_L - (cx + cl)
    pad12_end = c.PCB_L - (c.PAD_X0 + 11 * c.PAD_PITCH + c.PAD_R)
    m2_offset = c.PCB_Y + c.PCB_W / 2 - y1
    assert abs(m2_offset - (y2 - c.PCB_Y - c.PCB_W / 2)) < 1e-9, c.M2_XY
    return [
        ('ctrl5_hook_e', c.HOOK_E, '[v5 2단계 2026-11-09 시험 후보] 스냅 암 립이 PCB 긴 변 아래로 겹치는 깊이(PCB 가운데 놓임). '
         f"주문 1 시험편 A {a['hook_e']} / C {t['hook_e']}. 탄성 암 X {c.ARM_ROOT_X - c.ARM_FREE_X:.1f}·두께 {c.ARM_T_ROOT:.1f}(MJF 벽), "
         f"립까지 {report['lip_arm_mm']}, 삽입 변형률 약 {report['insert_strain_pct']:.1f}%(외팔보 계산, 실물 미확인)"),
        ('ctrl5_end_d', c.END_D, '[v5 2단계 시험 후보] +X 끝 립·받침이 PCB 끝을 덮는 길이. 패드 열 사이에서만 덮고 '
         f'크리스털(끝에서 {crystal_end:.1f}) 양옆으로 나눔. 12번 패드 링 끝 ↔ PCB 끝 {pad12_end:.2f}(검토 모델 참고 배치, M15 미실측). '
         f"시험편 A {a['end_d']} / C {t['end_d']}"),
        ('ctrl5_stop_gap', c.STOP_GAP, f"[v5 2단계 시험 후보] 암 끝 바깥면 ↔ 레일. 해제 이동 겸 과변형 제한(시험편 C {t['stop_gap']})"),
        ('ctrl5_clr_z', c.CLR_Z, f'[v5 2단계 설계 후보] PCB 면 ↔ 립·받침 Z 여유(편측). 립 윗면 Z {c.CATCH_Z:.2f}, 받침 Z {c.SUPPORT_Z:.2f}'),
        ('ctrl5_M2_1_X', x1, '[v5 2단계 2026-11-09] 브래킷 M2 앞(옛 125, 17: 배선 5번 패드 위 0.8에 너트 보스). 미배선 1–4번 구역, 패드 열 사이'),
        ('ctrl5_M2_1_Y', round(y1, 6), f'[v5 2단계 2026-11-09] 브래킷 M2 앞 Y = PCB 중심선 − {m2_offset:.1f}'),
        ('ctrl5_M2_2_X', x2, '[v5 2단계 2026-11-09] 브래킷 M2 뒤(옛 125, 25)'),
        ('ctrl5_M2_2_Y', round(y2, 6), f'[v5 2단계 2026-11-09] 브래킷 M2 뒤 Y = PCB 중심선 + {m2_offset:.1f}'),
    ]


def check_ctrl(evaluated, trials):
    """The generator's Pro Micro frame matches the document; each bracket is one closed body of the expected volume."""
    bodies = {b['name']: b for b in evaluated['bodies']}
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    c = ctrl_v5
    for name, value in [('TBD_ctrl_X', c.PCB_X), ('TBD_ctrl_Y', c.PCB_Y), ('TBD_ctrl_L', c.PCB_L), ('TBD_ctrl_W', c.PCB_W),
                        ('TBD_ctrl_pcb_Z', c.PCB_Z), ('REF_ctrl_pcb_T', c.PCB_T), ('TBD_ctrl_clr', c.CLR),
                        ('TBD_usb_plug_W', c.PLUG_W), ('split_bracket_gap', c.ROOF_GAP), ('split_bracket_T', c.ROOF_T),
                        ('split_M2_plate_seat_Z', c.M2_SEAT_Z), ('split_M2_clear_D', c.M2_CLEAR_D),
                        ('split_M2_head_D', c.M2_HEAD_D)]:
        assert abs(values[name] - value) < 1e-4, (name, values[name], value)
    assert abs(values['TBD_frame_T'] + values['TBD_standoff_H'] - c.PLATE_BOTTOM) < 1e-9
    assert 'CTRL_GATE_SPLIT_V1' not in bodies and 'REF_M2_GATE' not in bodies
    report = {}
    assert not set(c.TRIALS) & set(bodies), 'snap trials belong in model/ctrl_trials_v5.sc'
    bodies.update({b['name']: b for b in trials['bodies']})
    assert set(c.TRIALS) | set(REAR_REST_TRIALS) | set(seam_coupon_bodies()) == {b['name'] for b in trials['bodies']}, trials['bodies']
    for body, design in [(c.BODY, c.bracket())] + [(n, c.bracket(**s)) for n, s in c.TRIALS.items()]:
        b = bodies[body]
        expected = c.expected_volume(design)
        assert b['closed'], b
        assert abs(b['volume_mm3'] - expected) / expected < 0.015, (body, b['volume_mm3'], expected)
        report[body] = dict(volume_mm3=round(b['volume_mm3'], 3), estimate_mm3=round(expected, 3), bbox=b['bbox'])
    return report


def cover_params(doc):
    """Add the v5 cover, key margin and leg magnet parameters to doc; returns new_param() for further ones."""
    params = {p['name']: p for p in doc['params']}

    def new_param(name, expr, comment, unit='mm', before=None):
        p = dict(name=name, expr=str(expr), comment=comment, model=False, unit=unit)
        index = len(doc['params']) if before is None else doc['params'].index(params[before])
        doc['params'].insert(index, p)
        params[name] = p

    new_param('v5_rim_ref_Z', 14, 'Approximate PSD60 rim height for comparison only', before='TBD_cover_T')
    new_param('v5_legmag_skin_min', LEGMAG_SKIN_MIN, 'Minimum resin skin above the leg magnet pocket',
              before='TBD_cover_T')
    new_param('v5_keycap_bottom_above_seat', 6.0, '[v5 2차 r2 근거 2026-11-06] 쉴 때 키캡 스커트 밑면 − 스위치 착좌면. r2: 2T upper plate 위에서 '
              '키캡을 끝까지 누르면 유격이 거의 없다 → 바닥에서 착좌 + 약 2, 쉴 때 + 약 6. r2 실측(upper plate 윗면 → 스커트 밑면 g)으로 '
              '확정: 2 + g', before='TBD_cover_T')
    new_param('v5_keycap_bottom_rest_Z', 'plate_top_Z - TBD_upper_plate_T + v5_keycap_bottom_above_seat',
              '[v5 2차 유도값] 쉴 때 키캡 스커트 밑면 Z = 착좌 11.3 + 6.0 = 17.3', before='TBD_cover_T')
    # Z 19 kept (user 2026-11-10); the lower candidates 1.2 (Z 18.5) / 0.7 (Z 18) are tried on codex/46es-cover-plate-trial.
    new_param('v5_skirt_cover_H', 1.7, '[v5 2차 사용자 결정 2026-11-06] 턱이 쉴 때 키캡 옆면(스커트)을 덮는 높이. r2 약 3.0, v5 1차(평판 Z 18) 0.7. '
              '대안 1.2(턱 Z 18.5) / 0.7(Z 18)', before='TBD_cover_T')
    new_param('v5_cover_top_Z', 'v5_keycap_bottom_rest_Z + v5_skirt_cover_H',
              'Single flat cover top at Z 19', before='TBD_cover_T')
    new_param('v5_cover_top_above_rim', 'v5_cover_top_Z - v5_rim_ref_Z',
              'Flat cover top minus approximate rim height', before='TBD_cover_T')
    new_param('v5_legmag_skin', 'v5_cover_top_Z - plate_top_Z - TBD_magnet_T - TBD_magnet_clr',
              'Actual material over the lower leg magnet pocket', before='TBD_cover_T')
    # TBD_cover_T (cover top at v5_cover_top_Z) and TBD_upper_plate_T 1.7 (2026-11-06) are set in the base.
    # --- 3. key margin (documentation parameter; sketch rectangles are fixed numbers) -----------
    new_param('v5_key_margin', KEY_MARGIN, '[v5 사용자 목표 2026-11-06] 키캡(실제 폭, 바닥 외곽) ↔ 커버 창 최소 여유. '
              'SK35_COVER_SILHOUETTE_V5_* 창 윤곽은 이 여유를 담는 고정 숫자(tools/build_seam_v5.py에서 재생성)')
    # --- 3b. 커버 창 단순화 파라미터 (v5 2026-11-09) ---------------------------------------
    s = COVER_SILHOUETTE
    new_param('v5_cover_silhouette_cell', s['cell'], '[v5 2026-11-10] 커버 창 실루엣 래스터 셀 크기. 키 블록마다 실제 키캡 폭(r2 칸 폭 아님)의 회전 셀 사각형을 합침. '
              '키캡 18.05 + 2×v5_key_margin + 래스터·단순화 오차 0.3(시험값 16은 키캡 간격 0.31)')
    new_param('v5_cover_silhouette_close_r', s['close_r'], '[v5 2026-11-09] 오목 모서리 둥글림 반경(0 = 둥글림 없음, 직각 계단 유지)')
    new_param('v5_cover_silhouette_fill_L', s['fill_L'], '[v5 2026-11-09] 가로/세로 선분 닫힘 길이. 이보다 좁은 틈·쐐기를 직선으로 메움(계단 모서리 유지)')
    new_param('v5_cover_silhouette_min_rail', s['min_rail'], '[v5 2026-11-10] 커버 외곽 안쪽 최소 살 폭(창을 이 선에서 자름). '
              '9·31·40번 키캡+여유가 외곽 1.16 안까지 와서 1.1(레진 벽 한계 1.0)')
    new_param('v5_cover_silhouette_res', s['res'], '[v5 2026-11-09] 래스터 해상도')
    # --- 2. leg magnets ------------------------------------------------------------------------------
    new_param('v5_legmag_plate_clr', 0.15, '[v5 설계 후보] plate 쪽 다리 자석 포켓 반경 여유(Ø3.3). MJF ±0.3: 빡빡하면 Ø3.3 드릴로 손질, '
              '헐거우면 에폭시로 채움(plate 재출력 없음)')
    new_param('v5_legpad_L', 8, '[v5 설계 후보] 다리 자석 자리에서 plate 가장자리 단차(rabbet)를 메우는 받침 길이(X)')
    new_param('v5_lip_relief_clr', 0.3, '[v5 설계 후보] 받침 양끝 ↔ 커버 립 절단 끝 여유(X, 편측)')
    for s, (x, y, plate, cover) in LEG_MAGNETS.items():
        new_param(f'v5_legmag_{s}_X', x, f'[v5 2026-11-06] {s} 커버 아래 다리 끝 자석 쌍 X(래스터로 고른 고정값: 벽 ≥ 1.2)')
        new_param(f'v5_legmag_{s}_Y', y, f'[v5 2026-11-06] {s} 커버 아래 다리 끝 자석 쌍 Y(앞 가장자리 쪽)')
    return new_param


def emit_cover_cuts(doc, feature, sketch, plates=True):
    """Silhouette window and leg magnet features on the covers; with plates, also the plate pads, pockets and the
    reference magnets (in the production timeline order). Without plates (--covers) only the cover features."""
    top_plane = dict(type='offset', base=dict(type='origin', name='XY'),
                     distance='TBD_frame_T + TBD_standoff_H + TBD_plate_T + TBD_cover_T')
    # 커버 창 단순화: 기존 개별 키 마진 그룹 대신 실루엣 통합 윤곽 사용 (v5 2026-11-09)
    for i, poly in enumerate(cover_windows(), 1):
        sk = sketch(f'SK35_COVER_SILHOUETTE_V5_{i}', top_plane, [poly])
        feature('extrude', f'COVER_SILHOUETTE_V5_{i}', sketch=sk, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='negative',
                            distance='TBD_cover_T + TBD_cover_lip_H + 0.5'),
                operation='cut', targets=list(COVERS))

    front_plate = '-TBD_pcb0_dy + TBD_plate_gap'
    for s, (x, y, plate, cover) in LEG_MAGNETS.items():
        X, Y = f'v5_legmag_{s}_X', f'v5_legmag_{s}_Y'
        # plate: fill the rabbet under the leg tip (local support), then the pocket
        if plates:
            feature('box', f'PLATE_LEGPAD_{s}_V5', corner=[f'{X} - v5_legpad_L/2', front_plate,
                                                          'plate_top_Z - TBD_cover_lip_H - 0.05'],
                    length='v5_legpad_L', width='TBD_cover_wall + TBD_cover_lip_clr + 0.05',
                    height='TBD_cover_lip_H + 0.05', operation='join', participants=[plate])
        feature('box', f'COVER_LIP_RELIEF_{s}_V5', corner=[f'{X} - v5_legpad_L/2 - v5_lip_relief_clr',
                                                          '-TBD_pcb0_dy + TBD_cover_gap - 1',
                                                          'plate_top_Z - TBD_cover_lip_H - 0.5'],
                length='v5_legpad_L + 2*v5_lip_relief_clr', width='TBD_cover_wall + 1.5',
                height='TBD_cover_lip_H + 0.5', operation='cut', participants=[cover])
        feature('cylinder', f'COVER_LEGMAG_{s}_V5', axis=[0., 0., 1.], base=[X, Y, 'plate_top_Z - 1'],
                height='1 + TBD_magnet_T + TBD_magnet_clr', radius='(TBD_magnet_D + 2*TBD_magnet_clr) / 2',
                operation='cut', participants=[cover])
        if not plates:
            continue
        feature('cylinder', f'PLATE_LEGMAG_{s}_V5', axis=[0., 0., 1.],
                base=[X, Y, 'plate_top_Z - TBD_magnet_T - TBD_magnet_clr'],
                height='TBD_magnet_T + TBD_magnet_clr + 1', radius='(TBD_magnet_D + 2*v5_legmag_plate_clr) / 2',
                operation='cut', participants=[plate])
        for side, z in [('COVER', 'plate_top_Z + TBD_magnet_clr'),
                        ('PLATE', 'plate_top_Z - TBD_magnet_clr - TBD_magnet_T')]:
            name = f'REF_LEGMAG_{s}_{side}'
            feature('cylinder', name, axis=[0., 0., 1.], base=[X, Y, z], height='TBD_magnet_T',
                    radius='TBD_magnet_D / 2', operation='new_body', body_names=[name])
            doc['appearances']['bodies'][name] = copy.deepcopy(doc['appearances']['bodies'].get(
                'REF_SO1_MAGNET', dict(name='Custom', color=[167, 174, 181], opacity=1.0)))


def emit_code_bodies(doc, feature):
    """Covers, spine and reference hardware come from code (plan 4-5 steps 2-3): only their own features touch them,
    so they run after the base timeline with the BRep of the base-era chain. Sketch visibility is the base's:
    cover and spine sketches hidden, the four reference nut sketches shown."""
    first = doc['next_id']
    cover_v5.emit(feature)
    spine_v5.emit(feature)
    doc['visibility']['hidden_sketches'] += [f['id'] for f in doc['features']
                                             if f['id'] >= first and f['type'] == 'sketch']
    hardware_v5.emit(feature)


def build(probe=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    doc, container = read_source()
    new_param = cover_params(doc)
    feature, sketch = helpers(doc)
    emit_seam(doc, feature, sketch)
    s2 = seam_v5.COUPONS['S2'][0]
    new_param('v5_seam_fit', seam_v5.PRODUCTION.fit, '[2026-11-10 tools/seam_v5.py] 앞 이음 tab 옆면·걸림 턱의 위치결정 여유(편측). '
              f'주문 1 쿠폰 S2는 {s2.fit:g}, S0는 옛 dovetail')
    new_param('v5_seam_nut_AF', seam_v5.PRODUCTION.nut_AF, '[2026-11-10 tools/seam_v5.py] 앞 이음 너트 포켓 맞변(닫힌 육각, M2 너트 4.0을 눌러 끼움). '
              f'주문 1 쿠폰 S2는 {s2.nut_AF:g}, S0는 옛 {seam_v5.DOVETAIL.nut_AF:g}(이음면 쪽 열림)')
    new_param('v5_seam_tab_end_X', seam_v5.TAB_END_X, '[2026-11-10 tools/seam_v5.py] 앞 이음 tab 끝 X(L 조각의 오른쪽 끝). '
              f'걸림 턱은 X {seam_v5.NECK_END_X:g}부터 +Y로 {seam_v5.HOOK_Y:g}')
    emit_code_bodies(doc, feature)
    emit_cover_cuts(doc, feature, sketch)

    # --- rest blocks on the PSD60 rear-wall bosses (feet on the plate 2026-11-09, separate blocks 2026-11-10) ------
    rests = rear_rest_plan(doc)
    for i, x in enumerate(REAR_BOSS_X, 1):
        new_param(f'v5_rear_boss_{i}_X', x, f'[사진 추정·미실측 2026-11-09] PSD60 뒤 벽 안쪽 반원 보스 {i} 중심 X. 사용자 제공 '
                  'KPrepublic 제품 사진을 H01–H06으로 사영 보정(잔차 ≤ 0.8, 기준점 하나씩 빼면 ±2–4). 실측 M22'
                  + (' · 우 mount 뒤 모서리(SO4 옆) 밑이라 받침 블록 없음' if i == 4 else ''))
    new_param('v5_rear_boss_D', REAR_BOSS_D, '[사진 추정·미실측 2026-11-09] 뒤 벽 보스 지름(약 8–10). 벽에 반쯤 묻힌 반원. 실측 M22')
    new_param('v5_rear_boss_top_Z', REAR_BOSS_TOP_Z, '[가정 2026-11-09] 뒤 벽 보스 윗면 = 지지대 윗면. 근거: r2 맨 아래 판 P0(2T, 폭 4 테두리, '
              'H01·H05·H06 M2 구멍)가 노치 없이 이 보스 위를 지났다. 실측 M22')
    new_param('v5_rear_rest_gap', REAR_REST_GAP, '[v5 설계 2026-11-10] 뒤 받침 블록 밑면 ↔ 보스 윗면 공칭 틈 = 점착 패드 자리. 블록을 패드로 '
              '보스 위에 붙인다. 딱 맞춰 만들면 지지대 6개가 정한 plate 높이와 겹친다(과구속)')
    new_param('v5_rear_rest_L', REAR_REST_L, f'[v5 설계 2026-11-10] 뒤 받침 블록 길이(X). 보스 추정 위치가 ±{REAR_REST_CHORD_MARGIN:g} 틀려도 '
              '플랜지 안쪽 면에서 본 보스 윗면 폭이 블록 밑에 다 들어온다')
    new_param('v5_rear_rest_W', REAR_REST_W, '[v5 설계 2026-11-10] 뒤 받침 블록 폭(Y). plate 뒤 가장자리에서 안쪽으로: 플랜지 폭 split_flange_W + '
              f'보스 앞쪽으로 {REAR_REST_W - 2.0:g}')
    variants = ' / '.join(f'{REAR_REST_H + t["dh"]:g}' for t in REAR_REST_TRIALS.values())
    new_param('v5_rear_rest_H', 'plate_top_Z - TBD_plate_T - split_flange_H - v5_rear_boss_top_Z - v5_rear_rest_gap',
              f'[v5 유도값 2026-11-10] 뒤 받침 블록 높이 = 플랜지 밑면 − 보스 윗면 − 패드 틈. 주문 1 높이 변형 {variants}')
    for i, (x, plate) in REAR_RESTS.items():
        side = 'L' if plate.startswith('PLATE_L') else 'R'
        body = REAR_REST_BODY.format(i)
        new_param(f'v5_rear_rest_{i}_X', x, f'[v5 설계 2026-11-09] 뒤 받침 블록 {i} 중심 X(보스 {i} 위, plate {side} 뒤 플랜지 구간 안)')
        feature('box', body,
                corner=[f'v5_rear_rest_{i}_X - v5_rear_rest_L/2', f'{PLATE_REAR_Y} - v5_rear_rest_W',
                        'v5_rear_boss_top_Z + v5_rear_rest_gap'],
                length='v5_rear_rest_L', width='v5_rear_rest_W', height='v5_rear_rest_H',
                operation='new_body', body_names=[body])
        doc['appearances']['bodies'][body] = dict(name='Custom', color=REAR_REST_COLOR, opacity=1.0)

    # Phase 2 (2026-11-09): tools/ctrl_v5.py builds the snap bracket (the base has no bracket),
    # its two plate screw holes and the reference M2 screws. The order-1 trial variants A/C are built into
    # model/ctrl_trials_v5.sc (trials_document); their keep-out checks run here with the production bracket's.
    for name, expr, comment in ctrl_params():
        new_param(name, expr, comment)

    # Mounts: the four bodies are built under their order-1 names straight from the CADCraft drawing.
    mounts = mount_profiles()
    emit_mounts(feature, sketch, mounts)
    ctrl_report = dict(production=ctrl_v5.check())
    ctrl_v5.emit(feature, sketch)
    for body, spec in ctrl_v5.TRIALS.items():
        ctrl_report[body] = ctrl_v5.check(ctrl_v5.bracket(spec['hook_e'], spec['end_d'], spec['stop_gap']))

    doc['name'] = '46es seam v5 - flat cover, drawing-built mounts, snap controller bracket'
    seed = CACHE / 'seed_v5.sc'
    write_seed(doc, container, seed)
    pending = CACHE / 'v5.sc'
    csv_pending = CACHE / 'parameters_seam_v5.csv'
    csv_export = dict(command='parameters.export', params=dict(path=str(csv_pending), format='csv'))
    # The print exports of both orders ride on the saving call (export_print_v5.py reads them by the saved hash).
    evaluated, elapsed = evaluate(seed, pending, [csv_export, *prebuild(OUTPUT, pending)])
    seal_prebuilt(OUTPUT, pending)
    trials_seed, trials_pending = CACHE / 'seed_ctrl_trials_v5.sc', CACHE / 'ctrl_trials_v5.sc'
    write_seed(*trials_document(), trials_seed)
    trials, trials_elapsed = evaluate(trials_seed, trials_pending, prebuild(TRIALS_OUTPUT, trials_pending))
    seal_prebuilt(TRIALS_OUTPUT, trials_pending)
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    bodies = {b['name']: b for b in evaluated['bodies']}
    top_z = values['v5_cover_top_Z']
    spine_v5.check(values)
    cover_v5.check(bodies)
    assert values['v5_legmag_skin'] >= values['v5_legmag_skin_min']
    assert abs((values['TBD_magnet_D'] + 2 * values['TBD_magnet_clr']) / 2 - LEGMAG_POCKET_R) < 1e-9
    levels = top_levels(pending)
    for name, faces in levels.items():
        assert set(faces) == {round(top_z, 4)}, (name, faces)
        assert abs(bodies[name]['bbox']['max'][2] - top_z) < 1e-6, name
    mount_report = check_mounts(evaluated, mounts)
    ctrl_report['bodies'] = check_ctrl(evaluated, trials)
    seam_report = check_seam(evaluated, trials)
    rest_report = check_rear_rests(evaluated, trials, rests)
    rest_report['plan_clearance_mm'] = rear_rest_clearance(rests, mounts, bodies)
    active = sum(1 for f in evaluated['timeline'] if not f.get('suppressed'))
    info = dict(model=str(pending if probe else OUTPUT), base_sha=sha(BASE),
                bodies=evaluated['body_count'], timeline=len(evaluated['timeline']), active_features=active,
                run_seconds=round(elapsed, 1),
                trials_model=str(trials_pending if probe else TRIALS_OUTPUT), trials_run_seconds=round(trials_elapsed, 1),
                evaluation_ms=round(sum(f.get('ms', 0) for f in evaluated['timeline'])),
                cover_top_Z=top_z, cover_T=values['TBD_cover_T'], cover_levels=levels, mounts=mount_report,
                ctrl=ctrl_report, rear_rests=rest_report, seam=seam_report)
    if not probe:
        pending.replace(OUTPUT)
        trials_pending.replace(TRIALS_OUTPUT)
        csv_pending.replace(PARAMETERS_CSV)
        info['output_sha'] = sha(OUTPUT)
        write_build_record()
    write_json(CACHE / ('probe_v5.json' if probe else 'build_v5.json'), info)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return info


def refresh_record():
    """Record new input fingerprints for an edit that must not change the model (refactor, shared helper),
    without replacing the CAD. Rebuilding would give the same model in different zip bytes and make every
    record tied to the CAD file hash stale (order 1/2 source_sha256, verification, review model, renders).
    A probe build has to reproduce the committed document and every body's BRep exactly; otherwise regenerate."""
    build(probe=True)
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from cad_model import document, live_shapes
    count = 0
    for output, probe in ((OUTPUT, CACHE / 'v5.sc'), (TRIALS_OUTPUT, CACHE / 'ctrl_trials_v5.sc')):
        committed, rebuilt = document(output), document(probe)
        differ = [key for key in committed.keys() | rebuilt.keys() if committed.get(key) != rebuilt.get(key)]
        assert not differ, f'probe {output.name} differs from the committed CAD in {sorted(differ)}: run without --refresh-record'
        a, b = live_shapes(output), live_shapes(probe)
        bodies = sorted(n for n in a.keys() | b.keys() if a.get(n) != b.get(n))
        assert not bodies, f'probe bodies differ from {output.name}: {bodies}: run without --refresh-record'
        count += len(a)
    assert (CACHE / 'parameters_seam_v5.csv').read_bytes() == PARAMETERS_CSV.read_bytes(), 'parameter CSV differs'
    write_build_record()
    print(f'build record refreshed: {count} bodies identical, {OUTPUT.name} and {TRIALS_OUTPUT.name} kept')


def trials_document(rests=True):
    """Parameter-only copy of the base document holding the order-1 snap trials A and C and the rear rest height
    variants and the seam coupon pairs (tools/seam_v5.py). They are free bodies (no plate cut, no reference screws),
    so they need the parameters and nothing else."""
    doc, container = read_source()
    doc['features'] = []
    doc['next_id'] = 1
    doc['visibility'] = {key: [] for key in doc['visibility']}
    doc['appearances'] = {'bodies': {}}
    doc['name'] = '46es v5 order-1 trials: snap brackets A/C, rear rest height variants, seam coupons'
    feature, sketch = helpers(doc)
    for body, spec in ctrl_v5.TRIALS.items():
        ctrl_v5.emit(feature, sketch, ctrl_v5.bracket(**spec), body=body, plate=None, references=False)
    if rests:
        emit_rear_rest_trials(feature, doc)
        seam_v5.emit_coupons(feature, sketch, doc)
    return doc, container


def build_ctrl():
    """Fast loop for bracket work (plan 3-2): the production bracket B and the snap trials A/C alone, from a
    parameter-only document (no plate cut, no reference screws), against their keep-outs and volume estimates."""
    CACHE.mkdir(parents=True, exist_ok=True)
    doc, container = trials_document(rests=False)
    doc['name'] = '46es v5 snap brackets B, A, C only - bracket check'
    feature, sketch = helpers(doc)
    ctrl_v5.emit(feature, sketch, plate=None, references=False)
    designs = {ctrl_v5.BODY: ctrl_v5.bracket(), **{n: ctrl_v5.bracket(**s) for n, s in ctrl_v5.TRIALS.items()}}
    keep_outs = {name: ctrl_v5.check(design) for name, design in designs.items()}
    seed = CACHE / 'seed_ctrl_v5.sc'
    write_seed(doc, container, seed)
    evaluated, elapsed = evaluate(seed, CTRL_ONLY)
    bodies = {b['name']: b for b in evaluated['bodies']}
    assert set(bodies) == set(designs), sorted(bodies)
    report = {}
    for name, design in designs.items():
        b, expected = bodies[name], ctrl_v5.expected_volume(design)
        rel = abs(b['volume_mm3'] - expected) / expected
        assert b['closed'] and rel < 0.015, (name, b['closed'], b['volume_mm3'], expected)
        report[name] = dict(volume_mm3=round(b['volume_mm3'], 3), estimate_mm3=round(expected, 3),
                            rel_error=round(rel, 5), bbox=b['bbox'])
    info = dict(model=str(CTRL_ONLY), features=len(evaluated['timeline']), run_seconds=round(elapsed, 2),
                bodies=report, keep_outs=keep_outs)
    write_json(CACHE / 'ctrl_v5.json', info)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return info


def build_covers():
    """Fast loop for cover work (plan 3-2): the three cover pieces alone, from a parameter-only document, with the
    silhouette window and the leg magnet cuts (no plate, spine or reference parts). Checks the flat top, the piece
    ranges and the magnet skin, and reports whether each piece matches the production CAD's BRep."""
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from cad_model import live_shapes
    CACHE.mkdir(parents=True, exist_ok=True)
    doc, container = read_source()
    doc['features'] = []
    doc['next_id'] = 1
    doc['visibility'] = {key: [] for key in doc['visibility']}
    doc['name'] = '46es v5 cover pieces only - cover check'
    cover_params(doc)
    feature, sketch = helpers(doc)
    cover_v5.emit(feature)
    emit_cover_cuts(doc, feature, sketch, plates=False)
    seed = CACHE / 'seed_covers_v5.sc'
    write_seed(doc, container, seed)
    evaluated, elapsed = evaluate(seed, COVERS_ONLY)
    bodies = {b['name']: b for b in evaluated['bodies']}
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    assert set(bodies) == set(COVERS), sorted(bodies)
    cover_v5.check(bodies)
    assert values['v5_legmag_skin'] >= values['v5_legmag_skin_min']
    top_z = values['v5_cover_top_Z']
    levels = top_levels(COVERS_ONLY)
    for name, faces in levels.items():
        assert set(faces) == {round(top_z, 4)}, (name, faces)
    built, production = live_shapes(COVERS_ONLY), live_shapes(OUTPUT)
    info = dict(model=str(COVERS_ONLY), features=len(evaluated['timeline']), run_seconds=round(elapsed, 2),
                cover_top_Z=top_z, cover_levels=levels,
                bodies={n: dict(volume_mm3=round(bodies[n]['volume_mm3'], 3), bbox=bodies[n]['bbox'],
                                same_brep_as_production=built[n] == production.get(n)) for n in COVERS})
    write_json(CACHE / 'covers_v5.json', info)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return info


def build_mounts():
    """Fast loop for mount work: the four mounts alone, from a parameter-only copy of the base document."""
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from mesh_section import read_stl, compare
    CACHE.mkdir(parents=True, exist_ok=True)
    doc, container = read_source()
    doc['features'] = []
    doc['next_id'] = 1
    doc['visibility'] = {key: [] for key in doc['visibility']}
    doc['appearances'] = {'bodies': {}}
    doc['name'] = '46es v5 mounts only - drawing check'
    feature, sketch = helpers(doc)
    mounts = mount_profiles()
    emit_mounts(feature, sketch, mounts)
    seed = CACHE / 'seed_mounts_v5.sc'
    write_seed(doc, container, seed)
    evaluated, elapsed = evaluate(seed, MOUNTS_ONLY)
    report = check_mounts(evaluated, mounts)
    stl_dir = CACHE / 'mounts_stl'
    stl_dir.mkdir(exist_ok=True)
    script = [dict(command='file.export_stl', params=dict(path=str(stl_dir / f'{suffix}.stl'), bodies=[p['mount']], quality='fine'))
              for suffix, p in mounts.items()]
    write_json(CACHE / 'mounts_export.json', script, indent=None)
    run('run', str(CACHE / 'mounts_export.json'), '--in', MOUNTS_ONLY, '--quiet')
    sections = {}
    for suffix, p in mounts.items():
        sections[p['mount']] = compare(read_stl(stl_dir / f'{suffix}.stl'), expected_sections(p))
    ok = all(level['ok'] for body in sections.values() for level in body.values())
    warnings = [f['name'] for f in evaluated['timeline'] if f.get('warning')]
    info = dict(model=str(MOUNTS_ONLY), features=len(evaluated['timeline']), run_seconds=round(elapsed, 2),
                evaluation_ms=round(sum(f.get('ms', 0) for f in evaluated['timeline'])), warnings=warnings,
                bodies=report, sections=sections, sections_ok=ok)
    write_json(CACHE / 'mounts_v5.json', info)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    assert ok, 'mount sections differ from the drawing'
    return info


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', action='store_true', help='build into .cache/v5/v5.sc only and print the checks')
    ap.add_argument('--mounts', action='store_true', help='build and check only the four mounts (.cache/v5/mounts_v5.sc)')
    ap.add_argument('--refresh-record', action='store_true',
                    help='after a refactor: probe-build, require the committed CAD to be reproduced exactly, '
                         'and update model/seam_v5_build.json without replacing the CAD')
    ap.add_argument('--ctrl', action='store_true',
                    help='build and check only the brackets B, A, C (.cache/v5/ctrl_v5.sc)')
    ap.add_argument('--covers', action='store_true',
                    help='build and check only the three cover pieces (.cache/v5/covers_v5.sc)')
    a = ap.parse_args()
    if a.covers:
        build_covers()
    elif a.mounts:
        build_mounts()
    elif a.ctrl:
        build_ctrl()
    elif a.refresh_record:
        refresh_record()
    else:
        build(probe=a.probe)
