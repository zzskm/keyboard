"""Read documents and cached BRep bodies from SolidCraft models; no version-specific audit."""
import json, zipfile
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
