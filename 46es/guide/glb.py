"""One compact GLB for the 3D viewer, written from the CAD-exported binary STLs.

Each mesh welds identical vertices, stores positions as normalized uint16 in its own
bounding box (KHR_mesh_quantization, the node carries translation and scale) and drops
normals: the viewer and the 2D drawings recompute flat face normals from the winding.
That cuts the STLs to about a quarter, and GitHub Pages gzips .glb on top of that.
"""
import json
import struct

import numpy as np

STEPS = 65535  # uint16 grid across each mesh's box: under 0.005 mm for a 300 mm part
STL = np.dtype([('normal', '<f4', 3), ('verts', '<f4', (3, 3)), ('tag', '<u2')])


def read_stl(path):
    raw = path.read_bytes()
    count = struct.unpack_from('<I', raw, 80)[0] if len(raw) >= 84 else -1
    if count <= 0 or len(raw) != 84 + count * STL.itemsize:
        raise ValueError(f'Invalid binary STL: {path}')
    return np.frombuffer(raw, dtype=STL, count=count, offset=84)['verts']


def _pad(data, fill=b'\0'):
    return data + fill * (-len(data) % 4)


def write(path, meshes):
    """meshes: [(name, triangles (n, 3, 3) float)] -> GLB at path."""
    blob, views, accessors, gl_meshes, nodes = bytearray(), [], [], [], []

    def view(data, target, stride=None):
        views.append(dict(buffer=0, byteOffset=len(blob), byteLength=len(data), target=target,
                          **({'byteStride': stride} if stride else {})))
        blob.extend(_pad(data))
        return len(views) - 1

    for name, tris in meshes:
        points, index = np.unique(np.asarray(tris, '<f4').reshape(-1, 3), axis=0, return_inverse=True)
        lo, hi = points.min(axis=0).astype(float), points.max(axis=0).astype(float)
        scale = np.maximum(hi - lo, 1e-6)
        grid = np.round((points - lo) / scale * STEPS).astype('<u2')
        packed = np.zeros((len(grid), 4), '<u2')  # vertex attributes are 4-byte aligned: pad xyz to 8 bytes
        packed[:, :3] = grid
        kind = ('<u2', 5123) if len(points) < 65535 else ('<u4', 5125)
        accessors.append(dict(bufferView=view(packed.tobytes(), 34962, 8), componentType=5123, normalized=True,
                              count=len(grid), type='VEC3', min=grid.min(axis=0).tolist(), max=grid.max(axis=0).tolist()))
        accessors.append(dict(bufferView=view(index.reshape(-1).astype(kind[0]).tobytes(), 34963),
                              componentType=kind[1], count=index.size, type='SCALAR'))
        gl_meshes.append(dict(name=name, primitives=[dict(attributes=dict(POSITION=len(accessors) - 2),
                                                          indices=len(accessors) - 1)]))
        # normalized uint16 reads as 0..1, so the node maps it back to millimetres
        nodes.append(dict(name=name, mesh=len(gl_meshes) - 1, translation=[round(v, 5) for v in lo],
                          scale=[float(v) for v in scale]))

    doc = dict(asset=dict(version='2.0', generator='46es guide glb.py'),
               extensionsUsed=['KHR_mesh_quantization'], extensionsRequired=['KHR_mesh_quantization'],
               scene=0, scenes=[dict(nodes=list(range(len(nodes))))], nodes=nodes, meshes=gl_meshes,
               accessors=accessors, bufferViews=views, buffers=[dict(byteLength=len(blob))])
    text = _pad(json.dumps(doc, separators=(',', ':')).encode(), b' ')
    body = bytes(blob)
    out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(text) + 8 + len(body))
    out += struct.pack('<II', len(text), 0x4E4F534A) + text + struct.pack('<II', len(body), 0x004E4942) + body
    path.write_bytes(out)


def read(path):
    """GLB written by write() -> {name: triangles (n, 3, 3) float32 in millimetres}."""
    raw = path.read_bytes()
    magic, _, total = struct.unpack_from('<III', raw)
    if magic != 0x46546C67 or total != len(raw):
        raise ValueError(f'Invalid GLB: {path}')
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    body = memoryview(raw)[20 + size + 8:]

    def array(i, dtype, width):
        acc = doc['accessors'][i]
        bv = doc['bufferViews'][acc['bufferView']]
        data = np.frombuffer(body, dtype, offset=bv['byteOffset'], count=bv['byteLength'] // np.dtype(dtype).itemsize)
        return data.reshape(-1, width)[:acc['count']]

    meshes = {}
    for node in doc['nodes']:
        prim = doc['meshes'][node['mesh']]['primitives'][0]
        grid = array(prim['attributes']['POSITION'], '<u2', 4)[:, :3]
        kind = '<u2' if doc['accessors'][prim['indices']]['componentType'] == 5123 else '<u4'
        index = array(prim['indices'], kind, 1).reshape(-1)
        points = grid / STEPS * np.array(node['scale']) + np.array(node['translation'])
        meshes[node['name']] = points[index].reshape(-1, 3, 3).astype('<f4')
    return meshes
