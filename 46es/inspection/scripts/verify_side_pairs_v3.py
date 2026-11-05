"""Read-only v3 BRep/layout/CSV/mesh/volume audit; python -B this_file.py."""
import csv,hashlib,json
from verify_minimal_v2 import ROOT,live_shapes,document
from check_stl import check

def main():
    model=ROOT/'model/46es_mount_side_pairs_v3.sc'
    base=ROOT/'model/46es_mount_minimal_v2.sc'
    for name,sha in [('46es_draft_sketches.sc','e9c99ca1f38d741c7c0c6ae34efc56b172f9cb2bf38860c2bd277a28ba43b232'),
                     ('46es_mount_split_v1.sc','3ccfcea5cbddedf776c15c14f75efd3fe7eca30d2ff2f1ad769be1cda712681e'),
                     ('46es_mount_minimal_v2.sc','299517072bfc4f0328225dccab76dec0515674e09dba6a22020ad86670b5374d')]:
        assert hashlib.sha256((ROOT/'model'/name).read_bytes()).hexdigest()==sha,name
    source= document(ROOT/'model/46es_draft_sketches.sc');doc=document(model)
    for prefix in ['SK22','SK24','SK25','SK34']:
        assert next(x for x in source['features'] if x['name'].startswith(prefix))==next(x for x in doc['features'] if x['name'].startswith(prefix)),prefix
    params={p['name']:p['expr'] for p in doc['params'] if not p['model']}
    rows={p['name']:p for p in csv.DictReader((ROOT/'model/parameters_side_pairs_v3.csv').open(encoding='utf-8-sig'))}
    assert len(params)==len(rows)==187
    assert params=={n:p['expression'] for n,p in rows.items()}
    assert float(rows['side_pair_bridge_W']['value'])==8 and float(rows['side_pair_bridge_end_setback']['value'])==3.7
    old,new=live_shapes(base),live_shapes(model)
    assert len(new)==105
    common=set(old)&set(new);assert len(common)==103
    assert all(old[n]==new[n] for n in common),'changed common BRep'
    removed=set(old)-set(new)
    assert removed=={'MOUNT_H05_SO1_MIN_V2','MOUNT_H01_SO2_MIN_V2','MOUNT_H04_SO4_MIN_V2','MOUNT_H06_SO5_MIN_V2'},removed
    assert set(new)-set(old)=={'MOUNT_L_PAIR_V3','MOUNT_R_PAIR_V3'}
    parts=json.loads((ROOT/'inspection/data/side-pairs-v3-parts.json').read_text())['bodies'];assert len(parts)==9
    output=[]
    for p in parts:
        n=p['name'];assert len(new[n])==1 and len(new[n][0]['shells'])==1,n
        assert p['closed'] and p['kernel']['shells']==1,n
        assert p['bbox']['max'][0]-p['bbox']['min'][0]<=250,n
        mesh=check(str(ROOT/f'model/review_side_pairs_v3/{n}_REVIEW_ONLY.stl'))
        assert len(mesh['components'])==1 and mesh['bad_edge_count']==0,n
        comp=mesh['components'][0];rel=abs(comp['signed_volume']-p['volume_mm3'])/p['volume_mm3'];assert rel<0.001,(n,rel)
        for k in ['min','max']:assert max(abs(x-y) for x,y in zip(comp['bbox'][k],p['bbox'][k]))<0.05,n
        output.append(dict(name=n,volume_mm3=p['volume_mm3'],shells=1,mesh_components=1,bad_edges=0,mesh_relative_volume_error=rel))
    volumes={p['name']:p['volume_mm3'] for p in parts}
    pred=json.loads((ROOT/'inspection/data/side-pairs-v3-volume-prediction.json').read_text())
    residuals={p['side']:volumes[f"MOUNT_{p['side']}_PAIR_V3"]-p['expected_volume_mm3'] for p in pred}
    assert max(abs(x) for x in residuals.values())<0.03,residuals
    health=json.loads((ROOT/'inspection/data/side-pairs-v3-health.json').read_text())
    assert health==dict(bodies=105,features=401,sketches=60,dirty=False,dof_nonzero=[],errors=[],warnings=['HOUSING_POSTS_CAND'])
    clear=json.loads((ROOT/'inspection/data/side-pairs-v3-new-vs-all-clearance.json').read_text())
    assert clear['overlaps']==[] and clear['unchecked']==[] and clear['pairs_checked']+clear['pairs_pruned']==206
    print(json.dumps(dict(ok=True,bodies=105,features=401,sketches=60,unchanged_common_BReps=103,volume_prediction_residual_mm3=residuals,parts=output),indent=2))

if __name__=='__main__':main()
