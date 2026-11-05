"""Read-only audit of the saved split model, source layout, CSV and review STLs.

Run from the repository: python -B 46es/inspection/scripts/verify_split_v1.py
Does not rebuild, export or modify a SolidCraft design.
"""
import csv, hashlib, json, zipfile
from pathlib import Path
from read_sc_cache import read
from check_stl import check

ROOT=Path(__file__).resolve().parents[2]
MODEL=ROOT/'model/46es_mount_split_v1.sc'
SOURCE=ROOT/'model/46es_draft_sketches.sc'
PARTS=['MOUNT_R_SPLIT_V1','PLATE_L_SPLIT_V1','PLATE_R_SPLIT_V1',
       'CTRL_BRACKET_SPLIT_V1','PLATE_SPINE_V1','MOUNT_L_SPLIT_V1','CTRL_GATE_SPLIT_V1']

def document(p):
    with zipfile.ZipFile(p) as z: return json.loads(z.read('document.json'))

def main():
    a,b=document(SOURCE),document(MODEL)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='e9c99ca1f38d741c7c0c6ae34efc56b172f9cb2bf38860c2bd277a28ba43b232'
    for prefix in ['SK22','SK24','SK25','SK34']:
        assert next(f for f in a['features'] if f['name'].startswith(prefix))==next(f for f in b['features'] if f['name'].startswith(prefix)),prefix
    params={p['name']:p for p in b['params'] if not p['model']}
    rows={p['name']:p for p in csv.DictReader((ROOT/'model/parameters_split_v1.csv').open(encoding='utf-8-sig'))}
    assert len(rows)==len(params)==185
    for name,p in params.items(): assert p['expr']==rows[name]['expression'],name
    for name,value in {'TBD_so_AF':5,'TBD_so_pocket_D':1,'TBD_ctrl_Y':13.064485,
                       'split_M2_plate_seat_Z':10.2,'split_gate_cap_Z':6.4,'split_gate_nut_Z':7.8}.items():
        assert abs(float(rows[name]['value'])-value)<1e-9,name
    cache,body=read(MODEL)
    records=cache['model']['model_bodies']
    live=[records[i] for start,count in cache['model']['states'][-1]['bodies'] for i in range(start,start+count)]
    assert len(live)==111,len(live)
    measured={p['name']:p for p in json.loads((ROOT/'inspection/data/split-v1-print-parts-final.json').read_text())['bodies']}
    output=[]
    for name in PARTS:
        record=next(x for x in live if x['name']==name)
        slices=cache['bodies'][record['body']]
        assert len(slices)==1,(name,slices)
        shape=body(slices[0])['solid']
        assert len(shape['shells'])==1,name
        mesh=check(str(ROOT/f'model/review_split_v1/{name}_REVIEW_ONLY.stl'))
        assert len(mesh['components'])==1 and mesh['bad_edge_count']==0,name
        shell=mesh['components'][0]
        cad=measured[name]
        assert cad['closed'] and cad['kernel']['shells']==1,name
        assert cad['bbox']['max'][0]-cad['bbox']['min'][0]<=250,name
        rel=abs(shell['signed_volume']-cad['volume_mm3'])/cad['volume_mm3']
        assert rel<0.0003,(name,rel)
        for end in ['min','max']:
            assert max(abs(x-y) for x,y in zip(shell['bbox'][end],cad['bbox'][end]))<0.05,name
        output.append(dict(name=name,shells=1,mesh_components=1,bad_edges=0,stl_volume_relative_error=rel))
    plates=[measured[x] for x in ['PLATE_L_SPLIT_V1','PLATE_R_SPLIT_V1']]
    sizes=[max(p['bbox']['max'][j] for p in plates)-min(p['bbox']['min'][j] for p in plates) for j in range(2)]
    assert abs(sizes[0]-285.781)<1e-6 and abs(sizes[1]-95.334)<1e-6,sizes
    health=json.loads((ROOT/'inspection/data/split-v1-final-health.json').read_text())
    assert health['dirty'] is False and health['features']==339 and health['sketches']==44
    assert health['errors']==[] and health['dof_nonzero']==[]
    assert health['warnings']==['HOUSING_POSTS_CAND']
    print(json.dumps(dict(ok=True,bodies=111,features=339,sketches=44,outline=sizes,parts=output),indent=2))

if __name__=='__main__':main()
