"""Find walls thinner than a limit in binary STL parts (for the MJF minimum wall check).

python -I thin_wall_scan.py [--limit 1.0] [--warn 1.5] [--spacing 0.5] [--json OUT.json]
                            [--map PRINT_SET.json EVAL.json] STL...

From points spread over every facet, a ray goes straight into the material (against the
facet's outward normal). The distance to where it leaves the part again is the wall thickness
at that point. Points thinner than --warn are grouped (points within 2 mm of each other form one
group) and each group is listed with its smallest thickness and where it is.

Near the tip of any corner the ray is short too, so each group also gives `wall_min_mm`: the
smallest thickness among points whose exit facet faces back within 20 deg of the entry facet
(two near-parallel faces = a wall). A group with a small `min_mm` but `wall_min_mm` at or above
the limit (or None) is a corner, cusp or wedge tip, not a thin wall.

--map takes the print-set JSON (file -> body, print_flip_about_X) and a `solidcraft-cli eval`
JSON (body bbox) and also gives each group in assembly coordinates, undoing
tools/orient_print_stl.py (turn about X, then box moved to 0,0,0).

numpy and scipy only. Facets must be wound outward (the exported STLs are; checked by the sign of
the volume).
"""
import argparse, hashlib, json, os, struct, sys
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree


def read_stl(path):
    data = open(path, 'rb').read()
    n = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * n:
        raise ValueError(f'{path}: not a binary STL')
    rec = np.frombuffer(data, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]),
                        count=n, offset=84)
    return rec['v'].astype(np.float64)


def samples(tris, spacing):
    """Points on each facet: centroids of a k x k barycentric split, k from the longest edge."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    edge = np.max(np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1),
                            np.linalg.norm(a - c, axis=1)]), axis=0)
    k = np.clip(np.ceil(edge / spacing).astype(int), 1, 60)
    pts, owner = [], []
    for kk in np.unique(k):
        idx = np.nonzero(k == kk)[0]
        # centroids of the "upward" sub-triangles of a kk-split (kk*(kk+1)/2 of them; enough)
        uv = [((i + 1 / 3) / kk, (j + 1 / 3) / kk) for i in range(kk) for j in range(kk - i)]
        uv = np.array(uv)
        u, v = uv[:, 0][None, :, None], uv[:, 1][None, :, None]
        p = a[idx][:, None] + u * (b[idx] - a[idx])[:, None] + v * (c[idx] - a[idx])[:, None]
        pts.append(p.reshape(-1, 3))
        owner.append(np.repeat(idx, len(uv)))
    return np.concatenate(pts), np.concatenate(owner)


def thickness(tris, spacing=0.5, tmax=1.5, cell=1.5):
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    nrm = np.cross(b - a, c - a)
    area2 = np.linalg.norm(nrm, axis=1)
    keep = area2 > 1e-12
    nrm[keep] /= area2[keep, None]
    vol = np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6
    if vol <= 0:
        raise ValueError('facets are not wound outward (volume <= 0)')

    # grid of facets by their boxes
    lo = tris.min(axis=1) - 1e-6
    hi = tris.max(axis=1) + 1e-6
    org = lo.min(axis=0) - cell
    imin = np.floor((lo - org) / cell).astype(np.int64)
    imax = np.floor((hi - org) / cell).astype(np.int64)
    dims = imax.max(axis=0) + 2
    span = imax - imin + 1
    cnt = span.prod(axis=1)
    tri_rep = np.repeat(np.arange(len(tris)), cnt)
    local = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    sy, sz = span[tri_rep, 1], span[tri_rep, 2]
    cx = imin[tri_rep, 0] + local // (sy * sz)
    cy = imin[tri_rep, 1] + (local // sz) % sy
    cz = imin[tri_rep, 2] + local % sz
    key = (cx * dims[1] + cy) * dims[2] + cz
    order = np.argsort(key, kind='stable')
    key_sorted, tri_sorted = key[order], tri_rep[order]

    pts, owner = samples(tris, spacing)
    d = -nrm[owner]
    o = pts + d * 1e-5
    best = np.full(len(pts), np.inf)
    exit_dot = np.full(len(pts), np.nan)
    chunk = 20000
    for s in range(0, len(pts), chunk):
        oo, dd, ow = o[s:s + chunk], d[s:s + chunk], owner[s:s + chunk]
        e = oo + dd * tmax
        rlo = np.floor((np.minimum(oo, e) - org) / cell).astype(np.int64)
        rhi = np.floor((np.maximum(oo, e) - org) / cell).astype(np.int64)
        rspan = rhi - rlo + 1
        rcnt = rspan.prod(axis=1)
        ray = np.repeat(np.arange(len(oo)), rcnt)
        loc = np.arange(rcnt.sum()) - np.repeat(np.cumsum(rcnt) - rcnt, rcnt)
        ry, rz = rspan[ray, 1], rspan[ray, 2]
        k = ((rlo[ray, 0] + loc // (ry * rz)) * dims[1] + rlo[ray, 1] + (loc // rz) % ry) * dims[2] \
            + rlo[ray, 2] + loc % rz
        st = np.searchsorted(key_sorted, k, 'left')
        en = np.searchsorted(key_sorted, k, 'right')
        m = en - st
        ray2 = np.repeat(ray, m)
        pos = np.arange(m.sum()) - np.repeat(np.cumsum(m) - m, m) + np.repeat(st, m)
        tri2 = tri_sorted[pos]
        pair = np.unique(ray2 * len(tris) + tri2)
        ray2, tri2 = pair // len(tris), pair % len(tris)
        sel = tri2 != ow[ray2]
        ray2, tri2 = ray2[sel], tri2[sel]
        # keep exit facets only: the ray leaves the material through a facet facing along it
        sel = np.einsum('ij,ij->i', nrm[tri2], dd[ray2]) > 1e-6
        ray2, tri2 = ray2[sel], tri2[sel]
        # Moller-Trumbore
        A, B, C = a[tri2], b[tri2], c[tri2]
        e1, e2 = B - A, C - A
        D = dd[ray2]
        P = np.cross(D, e2)
        det = np.einsum('ij,ij->i', e1, P)
        ok = np.abs(det) > 1e-12
        inv = np.zeros_like(det)
        inv[ok] = 1 / det[ok]
        T = oo[ray2] - A
        u = np.einsum('ij,ij->i', T, P) * inv
        Q = np.cross(T, e1)
        v = np.einsum('ij,ij->i', D, Q) * inv
        t = np.einsum('ij,ij->i', e2, Q) * inv
        hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-4) & (t <= tmax)
        r_h, t_h, f_h = ray2[hit], t[hit], tri2[hit]
        if len(r_h):
            o_ = np.lexsort((t_h, r_h))
            r_h, t_h, f_h = r_h[o_], t_h[o_], f_h[o_]
            first = np.r_[True, r_h[1:] != r_h[:-1]]
            r_h, t_h, f_h = r_h[first], t_h[first], f_h[first]
            best[s + r_h] = t_h
            # entry facet normal is -dd; a wall leaves through a facet facing the other way (dot ~ -1)
            exit_dot[s + r_h] = np.einsum('ij,ij->i', nrm[f_h], -dd[r_h])
    return pts, best, d, exit_dot


def groups(pts, th, d, warn, radius=2.0, exit_dot=None, limit=1.0, wall_cos=-0.94):
    idx = np.nonzero(th < warn)[0]
    if len(idx) == 0:
        return []
    tree = cKDTree(pts[idx])
    pr = tree.query_pairs(radius, output_type='ndarray')
    g = coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(idx), len(idx)))
    n, lab = connected_components(g, directed=False)
    out = []
    for i in range(n):
        mem = idx[lab == i]
        j = mem[np.argmin(th[mem])]
        wall = mem[exit_dot[mem] < wall_cos] if exit_dot is not None else mem
        wall_min = float(th[wall].min()) if len(wall) else None
        out.append({'min_mm': round(float(th[j]), 3), 'points': int(len(mem)),
                    'wall_min_mm': None if wall_min is None else round(wall_min, 3),
                    'wall_points_below_limit': int((th[wall] < limit).sum()),
                    'at_print': [round(float(x), 3) for x in pts[j]],
                    'to_print': [round(float(x), 3) for x in pts[j] + d[j] * th[j]],
                    'dir_print': [round(float(x), 3) for x in d[j]],
                    'box_print': [[round(float(x), 2) for x in pts[mem].min(0)],
                                  [round(float(x), 2) for x in pts[mem].max(0)]]})
    return sorted(out, key=lambda r: r['min_mm'])


def to_assembly(p, flip, bbox):
    lo, hi = bbox
    if flip:
        return [p[0] + lo[0], hi[1] - p[1], hi[2] - p[2]]
    return [p[0] + lo[0], p[1] + lo[1], p[2] + lo[2]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stl', nargs='+')
    ap.add_argument('--limit', type=float, default=1.0)
    ap.add_argument('--warn', type=float, default=1.5)
    ap.add_argument('--spacing', type=float, default=0.5)
    ap.add_argument('--json')
    ap.add_argument('--map', nargs=2, metavar=('PRINT_SET', 'EVAL'))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    pmap = {}
    if args.map:
        ps = json.load(open(args.map[0], encoding='utf-8'))
        ev = json.load(open(args.map[1], encoding='utf-8'))
        bodies = {b['name']: b for b in ev['bodies']}
        for r in ps:
            if r['body'] not in bodies:
                continue
            bb = bodies[r['body']]['bbox']
            bb = (bb['min'], bb['max']) if isinstance(bb, dict) else (bb[0], bb[1])
            pmap[r['file']] = (r['print_flip_about_X'], bb)
    report = []
    for f in args.stl:
        name = os.path.splitext(os.path.basename(f))[0]
        tris = read_stl(f)
        pts, th, d, ed = thickness(tris, args.spacing, args.warn)
        gs = groups(pts, th, d, args.warn, exit_dot=ed, limit=args.limit)
        for g in gs:
            if name in pmap:
                flip, bb = pmap[name]
                for k in ('at', 'to'):
                    g[k + '_assembly'] = [round(float(x), 3) for x in to_assembly(g[k + '_print'], flip, bb)]
                g['box_assembly'] = [[round(float(x), 2) for x in to_assembly(c, flip, bb)]
                                     for c in g['box_print']]
        fin = th[np.isfinite(th)]
        wall_mins = [g['wall_min_mm'] for g in gs if g['wall_min_mm'] is not None]
        rec = {'file': name, 'stl_sha256': hashlib.sha256(open(f, 'rb').read()).hexdigest(),
               'facets': int(len(tris)), 'samples': int(len(pts)),
               'min_mm': round(float(fin.min()), 3) if len(fin) else None,
               'wall_min_mm': min(wall_mins) if wall_mins else None,
               'below_limit': [g for g in gs if g['min_mm'] < args.limit],
               'below_warn_count': sum(1 for g in gs if g['min_mm'] >= args.limit)}
        report.append(rec)
        print(f"{name}: facets {rec['facets']}, samples {rec['samples']}, "
              f"min {rec['min_mm']} (walls {rec['wall_min_mm']}), <{args.limit}: {len(rec['below_limit'])}, "
              f"<{args.warn}: {rec['below_warn_count']}")
        for g in rec['below_limit']:
            print('   ', g['min_mm'], 'wall', g['wall_min_mm'], 'n', g['points'], 'wall<lim', g['wall_points_below_limit'],
                  'asm', g.get('at_assembly'), '->', g.get('to_assembly'), 'dir', g['dir_print'])
    if args.json:
        json.dump({'limit_mm': args.limit, 'warn_mm': args.warn, 'spacing_mm': args.spacing,
                   'parts': report}, open(args.json, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
