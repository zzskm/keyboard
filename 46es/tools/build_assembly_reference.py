"""Rebuild the assembly review CAD without changing any production body.

Case-only parameters use the coarse PSD60 measurements. Switches/keycaps are
new illustrative geometry, informed by Thingiverse 421524 and 468651/KeyV2.
Run from the repository root: python tools/build_assembly_reference.py
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import zipfile

from make_key_dxf import load_keys, rect

ROOT = Path(__file__).resolve().parents[1]
CLI = Path('C:/Program Files/SolidCraft/solidcraft-cli.exe')
SOURCE = ROOT / 'model/46es_mount_seam_v4.sc'
OUTPUT = ROOT / 'model/46es_assembly_review.sc'
CACHE = ROOT / 'guide/.cache/reference'
MEASUREMENTS = ROOT / 'model/measurements/2026-11-04T111846Z.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    result = subprocess.run([str(CLI), *map(str, args)], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace')[-5000:])


def build():
    CACHE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as archive:
        doc = json.loads(archive.read('document.json'))
        container = archive.read('container.json')
    measured = json.loads(MEASUREMENTS.read_text(encoding='utf-8'))['items']

    def value(item, field):
        return measured[item]['fields'][field]['value']

    params = {p['name']: p for p in doc['params']}

    def param(name, expression, comment, unit='mm'):
        p = dict(name=name, expr=str(expression), comment=comment, model=False, unit=unit)
        doc['params'].append(p)
        params[name] = p

    # These parameters drive only the reference housing, never the printed parts.
    for name, number, comment in [
        ('in_W', value('M01', 'front_post'), 'M01: front/post level only; coarse measurement'),
        ('in_D', value('M02', 'left_post'), 'M02: left/post level only; coarse measurement'),
        ('support_H', value('M05', 'sup_H01'), 'M05: H01 only; other five heights assumed equal'),
        ('rim_F', value('M05', 'rim_F'), 'M05: support top to front rim; coarse measurement'),
        ('rim_B', value('M05', 'rim_B'), 'M05: support top to rear rim; coarse measurement'),
        ('out_W', 'TBD_case_out_W', 'M04: nominal document width; not measured'),
        ('out_D', 'TBD_case_out_D', 'M04: nominal document depth; not measured'),
        ('in_R', 'TBD_case_in_R', 'M03: unmeasured radius; previous assumption'),
        ('post_D', value('M10', 'H01_D'), 'M10: H01 only; other diameters assumed equal'),
        ('pcb0_dx', 'TBD_pcb0_dx', 'M07: unmeasured origin offset; previous assumption'),
        ('pcb0_dy', 'TBD_pcb0_dy', 'M07: unmeasured origin offset; previous assumption'),
        ('out_xL', '(REF_PSD_out_W-REF_PSD_in_W)/2 + REF_PSD_pcb0_dx', 'Symmetric exterior margin assumption'),
        ('out_yF', '(REF_PSD_out_D-REF_PSD_in_D)/2 + REF_PSD_pcb0_dy', 'Symmetric exterior margin assumption'),
        ('out_yB', 'REF_PSD_out_D-REF_PSD_out_yF', 'Nominal rear exterior boundary'),
        ('bottom_F', 'REF_WIL_bot_zF', 'Unmeasured underside profile retained from old proxy'),
        ('bottom_B', 'REF_WIL_bot_zB', 'Unmeasured underside profile retained from old proxy'),
    ]:
        param('REF_PSD_' + name, number, comment)
    for h in range(1, 7):
        for axis in ('X', 'Y'):
            name = f'H{h:02}_{axis}'
            field = name[:-1] + axis.lower()
            expression = (f"{value('M08', field)} - REF_PSD_pcb0_d{axis.lower()}"
                          if field in measured['M08']['fields'] else f'CAND_{name}')
            param('REF_PSD_' + name, expression,
                  'M08: measured wall distance minus assumed origin offset' if field in measured['M08']['fields']
                  else 'M08: not measured; GH60 candidate retained')

    mapping = {'TBD_case_in_W': 'REF_PSD_in_W', 'TBD_case_in_D': 'REF_PSD_in_D',
               'TBD_case_in_R': 'REF_PSD_in_R', 'TBD_pcb0_dx': 'REF_PSD_pcb0_dx',
               'TBD_pcb0_dy': 'REF_PSD_pcb0_dy', 'TBD_support_H': 'REF_PSD_support_H',
               'TBD_case_post_D': 'REF_PSD_post_D', 'TBD_support_to_rim_F': 'REF_PSD_rim_F',
               'TBD_support_to_rim_B': 'REF_PSD_rim_B', 'REF_WIL_out_xL': 'REF_PSD_out_xL',
               'REF_WIL_out_W': 'REF_PSD_out_W', 'REF_WIL_out_yF': 'REF_PSD_out_yF',
               'REF_WIL_out_yB': 'REF_PSD_out_yB', 'REF_WIL_bot_zF': 'REF_PSD_bottom_F',
               'REF_WIL_bot_zB': 'REF_PSD_bottom_B'}
    mapping.update({f'CAND_H{h:02}_{a}': f'REF_PSD_H{h:02}_{a}' for h in range(1, 7) for a in ('X', 'Y')})

    def replace(obj, substitutions):
        if isinstance(obj, str):
            return re.sub(r'\b[A-Za-z_]\w*\b', lambda m: substitutions.get(m[0], m[0]), obj)
        if isinstance(obj, list):
            return [replace(x, substitutions) for x in obj]
        if isinstance(obj, dict):
            return {k: replace(v, substitutions) for k, v in obj.items()}
        return obj

    # Clone the shared cavity sketch: editing SK00 would resize production bodies.
    cavity = copy.deepcopy(doc['features'][0])
    cavity['id'] = doc['next_id']; doc['next_id'] += 1
    cavity['name'] = 'SK_PSD60_MEASURED_CAVITY_REF'
    cavity['sketch']['points'] = cavity['sketch']['points'][:15]
    cavity['sketch']['curves'] = cavity['sketch']['curves'][:8]
    cavity['sketch']['constraints'] = cavity['sketch']['constraints'][:20]
    cavity['sketch'].pop('links', None)

    def isolate(feature):
        aliases = dict(mapping)
        # Model dimensions must also be cloned; their original expressions drive production CAD.
        used = set(re.findall(r'\bd\d+\b', json.dumps(feature)))
        for name in used:
            if name not in params:
                continue
            other = 'ref_psd_' + name
            aliases[name] = other
            p = copy.deepcopy(params[name]); p['name'] = other
            p['expr'] = replace(p['expr'], mapping)
            doc['params'].append(p)
        return replace(feature, aliases)

    cavity = isolate(cavity)
    housing_name = 'REF_HOUSING_PSD60_MEASURED'
    names = {'REF_HOUSING_WILMORE_NOT_PSD60': housing_name}
    for i in range(5, 11):
        doc['features'][i] = replace(isolate(doc['features'][i]), names)
    doc['features'][5]['name'] = 'SK40_HOUSING_PROFILE_PSD60_REF'
    doc['features'][6]['name'] = 'HOUSING_OUTER_PSD60_NOMINAL_REF'
    doc['features'][7]['sketch'] = cavity['id']
    # Resolve the cavity against its own measured inner envelope.
    doc['features'].insert(7, cavity)
    doc['visibility'] = replace(doc['visibility'], names)
    doc['appearances'] = replace(doc['appearances'], names)
    for feature in doc['features']:
        if feature['id'] in (242, 243, 244):
            feature['suppressed'] = True
    doc['name'] = '46es v4 assembly review - PSD60 measured proxy / MX / OEM keycaps'
    seed = CACHE / 'seed.sc'
    with zipfile.ZipFile(seed, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('document.json', json.dumps(doc, ensure_ascii=False))
        archive.writestr('container.json', container)

    # Write native timeline features in one batch, then let SolidCraft evaluate
    # and save them once. Hundreds of interactive sketch commands needlessly
    # rebuild the same growing reference geometry after each individual line.
    def feature(kind, name, **kwargs):
        fid = doc['next_id']; doc['next_id'] += 1
        doc['features'].append(dict(id=fid, type=kind, name=name, suppressed=False, **kwargs))
        return fid

    def sketch(name, z=0, polygons=(), circles=(), plane=None):
        points = [dict(id='origin', pos=[0.,0.], fixed=True)]
        curves = []
        for poly in polygons:
            first = len(points)
            for x,y in poly:
                points.append(dict(id=f'p{len(points)}', pos=[x,y], fixed=True))
            for j in range(len(poly)):
                curves.append(dict(id=f'l{len(curves)+1}', type='line', construction=False,
                                   a=first+j, b=first+(j+1)%len(poly)))
        for center, radius in circles:
            points.append(dict(id=f'c{len(curves)+1}.center',pos=center,fixed=True))
            curves.append(dict(id=f'c{len(curves)+1}',type='circle',c=len(points)-1,r=radius,construction=False))
        plane = plane or dict(type='offset',base=dict(type='origin',name='XY'),distance=str(z))
        return feature('sketch', 'SK_'+name, plane=plane,
                       sketch=dict(points=points,curves=curves,constraints=[],counters=dict(p=len(points),l=len(curves))))

    def extrusion(name, sk, height, bodies=None, targets=None, taper=None):
        extent = dict(convention='total_distance',direction='positive',distance=str(height))
        if taper is not None: extent['taper']=str(taper)
        options = dict(targets=targets) if targets else dict(body_names=bodies)
        return feature('extrude',name,sketch=sk,profiles=dict(type='all'),extent=extent,
                       operation='join' if targets else 'new_body',**options)

    keys = load_keys(.693,.667)
    def names(prefix, count=46):
        return [prefix]+[f'{prefix} ({i})' for i in range(2,count+1)]
    def rectangles(w,h):
        return [rect(k['x'],k['y'],w,h,k['rot']) for k in keys]
    def layer(name,z,polygons,height,targets=None,taper=None):
        extrusion(name,sketch(name,z,polygons),height,bodies=names(name),targets=targets,taper=taper)
    def located(poly,k):
        a=math.radians(k['rot']);c,s=math.cos(a),math.sin(a)
        return [[k['x']+x*c-y*s,k['y']+x*s+y*c] for x,y in poly]

    lower='REF_MX_LOWER'
    layer(lower,5.5,rectangles(13.98,13.98),5.5)
    layer('REF_MX_FLANGE',11,rectangles(15.64,15.64),.82,targets=names(lower))
    layer('REF_MX_UPPER',11.82,rectangles(14.58,14.58),4.48,
          taper=-math.degrees(math.atan((14.58-10.62)/2/4.48)))
    cross=[(-2.25,-.575),(-.675,-.575),(-.675,-2.25),(.675,-2.25),
           (.675,-.575),(2.25,-.575),(2.25,.575),(.675,.575),(.675,2.25),
           (-.675,2.25),(-.675,.575),(-2.25,.575)]
    layer('REF_MX_STEM',16.3,[located(cross,k) for k in keys],4)
    guides=[(located([(x,0)],k)[0],r) for k in keys for x,r in [(0,1.925),(-4.95,.8),(4.95,.8)]]
    # Separate reference solids avoid an expensive 138-tool boolean union.
    extrusion('REF_MX_GUIDE',sketch('REF_MX_GUIDES',2.4,circles=guides),3.1,
              bodies=names('REF_MX_GUIDE',138))
    pins=[]
    for k in keys:
        for x,y in [(-3.77,2.7),(2.7,5.2)]:
            pins.append(located([(x-.43,y-.1),(x+.43,y-.1),(x+.43,y+.1),(x-.43,y+.1)],k))
    pin_names=names('REF_MX_CONTACT',92)
    extrusion('REF_MX_CONTACT',sketch('REF_MX_CONTACT',2.4,pins),3.1,bodies=pin_names)

    # OEM profile values from KeyV2/oem.scad. Three alpha rows use OEM R2/R3/R4;
    # thumbs and the bottom arrow row use R5. Exact keyset row assignment is assumed.
    rows={2:[3,6,9,11,14,17,25,28,31,33,36,39,18],
          3:[2,5,8,10,13,16,24,27,30,32,35,38],
          4:[1,4,7,12,15,23,26,29,34,37,43],1:[19]}
    profiles={1:(9.45,1),2:(9.,6),3:(9.25,9),4:(9.25,10),5:(11.2,-3)}
    for i,k in enumerate(keys,1):
        row=next((r for r,ids in rows.items() if i in ids),5)
        depth,tilt=profiles[row]
        k.update(oem_row=row,depth=depth,tilt=tilt)
        angle=math.radians(k['rot']);a=math.radians(tilt)
        xd=[math.cos(angle),math.sin(angle),0]
        yd=[-math.sin(angle)*math.cos(a),math.cos(angle)*math.cos(a),math.sin(a)]
        normal=[math.sin(angle)*math.sin(a),-math.cos(angle)*math.sin(a),math.cos(a)]
        width=18.05+(k['w_u']-1)*19.05
        center=[k['x']-1.75*math.sin(angle),k['y']+1.75*math.cos(angle),15.2+depth]
        plane=dict(type='custom',plane=dict(origin=center,x_dir=xd,y_dir=yd))
        bottom=sketch(f'KEYCAP_{i:02}_BASE',15.2,[rect(k['x'],k['y'],width,18.05,k['rot'])])
        top=sketch(f'KEYCAP_{i:02}_TOP',polygons=[rect(0,0,width-5.8,14.05,0)],plane=plane)
        cap=f'REF_KEYCAP_OEM_{i:02}'
        feature('loft',cap,sections=[dict(sketch=bottom,profiles=dict(type='all')),
                                   dict(sketch=top,profiles=dict(type='all'))],
                operation='new_body',body_names=[cap])
        doc.setdefault('appearances',{}).setdefault('bodies',{})[cap]=dict(name='Custom',color=[231,235,239],opacity=1)
        doc['visibility'].setdefault('hidden_bodies',[]).append(cap)
    for group,color in [('REF_MX_LOWER',[210,199,165]),('REF_MX_UPPER',[238,228,200]),
                        ('REF_MX_STEM',[231,189,53])]:
        for name in names(group):
            doc['appearances']['bodies'][name]=dict(name='Custom',color=color,opacity=1)
    doc['name']='46es v4 assembly review - measured PSD60 proxy / MX / OEM'
    with zipfile.ZipFile(seed,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('document.json',json.dumps(doc,ensure_ascii=False))
        archive.writestr('container.json',container)
    pending=CACHE/'review.sc'
    run('run','--in',seed,'--save',pending,'--quiet')
    report = CACHE / 'eval.json'
    run('eval', '--in', pending, '--json-out', report)
    evaluated = json.loads(report.read_text(encoding='utf-8'))
    failed = [f for f in evaluated['timeline'] if f.get('error')]
    assert not failed, failed
    pending.replace(OUTPUT)
    manifest = dict(source=SOURCE.name, source_sha=sha(SOURCE), measurement_sha=sha(MEASUREMENTS),
                    generator_sha=sha(Path(__file__)), output_sha=sha(OUTPUT),
                    keys=keys, housing=housing_name, body_count=evaluated['body_count'])
    (ROOT / 'model/assembly_reference.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(dict(model=str(OUTPUT), bodies=evaluated['body_count'], keys=len(keys))))


if __name__ == '__main__':
    build()
