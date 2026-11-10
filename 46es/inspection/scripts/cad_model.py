"""Read documents and cached BRep bodies from SolidCraft models; no version-specific audit."""
import hashlib, json, zipfile
from pathlib import Path
from read_sc_cache import read

ROOT = Path(__file__).resolve().parents[2]

def document(path):
    with zipfile.ZipFile(path) as z:return json.loads(z.read('document.json'))

def live_shapes(path):
    cache,body=read(path); records=cache['model']['model_bodies']
    live=[records[i] for start,count in cache['model']['states'][-1]['bodies'] for i in range(start,start+count)]
    out={}
    for r in live:
        slices=cache['bodies'][r['body']]
        out[r['name']]=[body(i)['solid'] for i in slices]
    return out

def shape_digest(solids):
    """SHA-256 of one body's cached BRep (live_shapes value) as canonical JSON. It holds geometry only (no feature
    ids), so a rebuild that reproduces a body keeps its digest and any change to it, however small, gives another
    (plan 3-4)."""
    return hashlib.sha256(json.dumps(solids,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def shape_digests(path):
    return {name:shape_digest(solids) for name,solids in live_shapes(path).items()}
