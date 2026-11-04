"""Point-splat orthographic renderer for a triangle soup saved by stl_overview.py.
usage: render.py mesh.npz out.png view [scale_px_per_mm] [comp_mask.npy] [zclip_lo zclip_hi]
view: top | bottom | front | back | left | right | iso
"""
import sys, zlib, struct
import numpy as np

def write_png(path, img):
    h, w, _ = img.shape
    raw = b''.join(b'\x00' + img[y].tobytes() for y in range(h))
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)

def render(V, nrm, area, view, s=3.0, color=None):
    # rotation: map world to (u right, v up, d toward viewer)
    if view == 'top':
        R = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    elif view == 'bottom':
        R = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], float)
    elif view == 'front':  # looking +Y
        R = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
    elif view == 'back':
        R = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float)
    elif view == 'left':  # looking +X
        R = np.array([[0, -1, 0], [0, 0, 1], [-1, 0, 0]], float)
    elif view == 'right':
        R = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)
    elif view == 'iso':
        a, b = np.radians(-30), np.radians(55)
        Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
        R = Rx @ Rz
    W = V @ R.T  # (n,3,3)
    N = nrm @ R.T
    # sample points per triangle
    step = 1.0 / s
    k = np.clip(np.ceil(np.sqrt(area) / step * 1.6).astype(int), 1, 60)
    pts, sh, cols = [], [], []
    light = np.array([0.3, 0.5, 0.8]); light /= np.linalg.norm(light)
    shade = np.abs(N @ light) * 0.75 + 0.25
    for kk in np.unique(k):
        idx = np.where(k == kk)[0]
        g = np.linspace(0, 1, kk + 1)
        a_, b_ = np.meshgrid(g, g)
        m = a_ + b_ <= 1
        a_, b_ = a_[m], b_[m]
        T = W[idx]
        P = T[:, None, 0] + a_[None, :, None] * (T[:, None, 1] - T[:, None, 0]) + b_[None, :, None] * (T[:, None, 2] - T[:, None, 0])
        pts.append(P.reshape(-1, 3))
        sh.append(np.repeat(shade[idx], len(a_)))
        cols.append(np.repeat(idx, len(a_)))
    P = np.concatenate(pts); S = np.concatenate(sh); C = np.concatenate(cols)
    umin, vmin = P[:, 0].min(), P[:, 1].min()
    iu = ((P[:, 0] - umin) * s).astype(int) + 10
    iv = ((P[:, 1] - vmin) * s).astype(int) + 10
    w, h = iu.max() + 11, iv.max() + 11
    pix = iv * w + iu
    order = np.lexsort((P[:, 2], pix))
    last = np.r_[pix[order][1:] != pix[order][:-1], True]
    sel = order[last]
    img = np.full((h * w, 3), 255, np.uint8)
    base = np.array([180, 180, 190], float) if color is None else None
    if color is None:
        c = np.outer(S[sel], [200, 200, 215])
    else:
        c = color[C[sel]] * S[sel, None]
    img[pix[sel]] = np.clip(c, 0, 255).astype(np.uint8)
    img = img.reshape(h, w, 3)[::-1]
    return img, (umin, vmin, s)

if __name__ == '__main__':
    d = np.load(sys.argv[1])
    V, nrm, area = d['V'].astype(float), d['nrm'].astype(float), d['area'].astype(float)
    view = sys.argv[3]
    s = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
    color = None
    if len(sys.argv) > 5 and sys.argv[5] != '-':
        lab = np.load(sys.argv[5])
        pal = np.array([[200, 200, 215], [230, 120, 90], [90, 160, 230], [120, 200, 120], [230, 200, 80], [200, 120, 220], [120, 220, 220], [160, 160, 160]], float)
        color = pal[lab % len(pal)]
    if len(sys.argv) > 7:
        lo, hi = float(sys.argv[6]), float(sys.argv[7])
        zc = V[:, :, 2].mean(1)
        m = (zc >= lo) & (zc <= hi)
        V, nrm, area = V[m], nrm[m], area[m]
        if color is not None:
            color = color[m]
    img, meta = render(V, nrm, area, view, s, color)
    write_png(sys.argv[2], img)
    print('wrote', sys.argv[2], img.shape, 'origin(u,v)=', meta)
