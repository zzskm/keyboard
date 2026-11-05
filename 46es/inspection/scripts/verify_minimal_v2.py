"""Read-only native CAD/STL/layout audit. Run from repository with python -B."""
import csv, hashlib, json, zipfile
from pathlib import Path
from read_sc_cache import read
from check_stl import check

ROOT=Path(__file__).resolve().parents[2]
MODEL=ROOT/'model/46es_mount_minimal_v2.sc'
BASE=ROOT/'model/46es_mount_split_v1.sc'
SOURCE=ROOT/'model/46es_draft_sketches.sc'

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

def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='e9c99ca1f38d741c7c0c6ae34efc56b172f9cb2bf38860c2bd277a28ba43b232'
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='3ccfcea5cbddedf776c15c14f75efd3fe7eca30d2ff2f1ad769be1cda712681e'
    source,base,doc=map(document,[SOURCE,BASE,MODEL])
    for prefix in ['SK22','SK24','SK25','SK34']:
        a=next(f for f in source['features'] if f['name'].startswith(prefix))
        b=next(f for f in doc['features'] if f['name'].startswith(prefix))
        assert a==b,prefix
    params={p['name']:p['expr'] for p in doc['params'] if not p['model']}
    csv_params={p['name']:p['expression'] for p in csv.DictReader((ROOT/'model/parameters_minimal_v2.csv').open(encoding='utf-8-sig'))}
    assert len(params)==185 and params==csv_params
    old,new=live_shapes(BASE),live_shapes(MODEL)
    assert len(new)==107
    common=set(old)&set(new)
    assert len(common)==101,len(common)
    assert all(old[n]==new[n] for n in common),'unchanged body exact BRep comparison'
    assert 'MOUNT_L_SPLIT_V1' not in new and 'MOUNT_R_SPLIT_V1' not in new
    assert not any(n.startswith(('MASK_','REF_M2_LAP_')) for n in new)
    parts=json.loads((ROOT/'inspection/data/minimal-v2-parts.json').read_text())['bodies']
    assert len(parts)==11
    out=[]
    for p in parts:
        n=p['name']; solids=new[n]
        assert len(solids)==1 and len(solids[0]['shells'])==1,n
        assert p['closed'] and p['kernel']['shells']==1,n
        assert p['bbox']['max'][0]-p['bbox']['min'][0]<=250,n
        mesh=check(str(ROOT/f'model/review_minimal_v2/{n}_REVIEW_ONLY.stl'))
        assert len(mesh['components'])==1 and mesh['bad_edge_count']==0,n
        comp=mesh['components'][0]
        rel=abs(comp['signed_volume']-p['volume_mm3'])/p['volume_mm3']
        assert rel<0.001,(n,rel)
        for side in ['min','max']:
            assert max(abs(x-y) for x,y in zip(comp['bbox'][side],p['bbox'][side]))<0.05,n
        out.append(dict(name=n,volume_mm3=p['volume_mm3'],shells=1,mesh_components=1,bad_edges=0,stl_relative_volume_error=rel))
    health=json.loads((ROOT/'inspection/data/minimal-v2-health.json').read_text())
    assert health['bodies']==107 and health['features']==395 and health['sketches']==58
    assert health['dirty'] is False and health['dof_nonzero']==[] and health['errors']==[]
    assert health['warnings']==['HOUSING_POSTS_CAND']
    print(json.dumps(dict(ok=True,bodies=107,features=395,sketches=58,exactly_preserved_common_bodies=len(common),parts=out),indent=2))

if __name__=='__main__':main()
