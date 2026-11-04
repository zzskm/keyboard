"""Overview of a binary STL: bbox, triangle count, manifoldness, volume, dominant normals."""
import sys, struct
import numpy as np

path = sys.argv[1]
out = sys.argv[2]
with open(path, 'rb') as f:
    hdr = f.read(80)
    n = struct.unpack('<I', f.read(4))[0]
    dt = np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    data = np.fromfile(f, dtype=dt, count=n)
print('header:', hdr.rstrip(b'\0')[:80])
print('triangles:', n, 'read:', len(data))
V = data['v'].astype(np.float64)
P = V.reshape(-1, 3)
print('bbox min', P.min(0), 'max', P.max(0), 'size', P.max(0) - P.min(0))
# unique vertices
q = np.round(P, 4)
uv, inv = np.unique(q, axis=0, return_inverse=True)
inv = inv.reshape(-1, 3)
print('unique verts', len(uv))
# edges
e = np.sort(np.concatenate([inv[:, [0, 1]], inv[:, [1, 2]], inv[:, [2, 0]]]), axis=1)
ue, cnt = np.unique(e, axis=0, return_counts=True)
print('edges', len(ue), 'boundary(1)', (cnt == 1).sum(), 'nonmanifold(>2)', (cnt > 2).sum())
# volume
v0, v1, v2 = V[:, 0], V[:, 1], V[:, 2]
vol = np.einsum('ij,ij->i', v0, np.cross(v1, v2)).sum() / 6
print('signed volume mm3', vol)
# face normals and areas
cr = np.cross(v1 - v0, v2 - v0)
area = np.linalg.norm(cr, axis=1) / 2
nrm = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
print('total area', area.sum())
# dominant normal directions (area weighted, rounded)
key = np.round(nrm, 2)
uk, ik = np.unique(key, axis=0, return_inverse=True)
s = np.bincount(ik.ravel(), weights=area)
order = np.argsort(-s)[:25]
print('dominant normals (area):')
for i in order:
    print('  ', uk[i], round(s[i], 1))
# connected components via union-find on triangles sharing vertices
parent = np.arange(len(uv))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
for a, b in ue:
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb
roots = np.array([find(i) for i in range(len(uv))])
ur, rc = np.unique(roots, return_counts=True)
print('components (by vertex):', len(ur))
comp_tri = roots[inv[:, 0]]
for r in ur[np.argsort(-rc)][:10]:
    m = comp_tri == r
    pts = V[m].reshape(-1, 3)
    vv = np.einsum('ij,ij->i', v0[m], np.cross(v1[m], v2[m])).sum() / 6
    print('  comp tris', m.sum(), 'bbox', pts.min(0).round(3), pts.max(0).round(3), 'vol', round(vv, 1))
np.savez_compressed(out, V=V.astype(np.float32), nrm=nrm.astype(np.float32), area=area.astype(np.float32))
