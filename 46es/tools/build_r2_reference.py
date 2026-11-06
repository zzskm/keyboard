#!/usr/bin/env python3
"""Reconstruct r2 panels from the audited DWG entity dump. Comparison only.
Requires CadQuery 2.6.x (includes ezdxf). Never modifies production v5 CAD.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'model/reference_r2'
SOURCE = ROOT / 'inspection/data/cadcraft_modelspace_entities.json'
PANELS = ROOT / 'inspection/data/geom_loops_panels.json'
CONFIG = ROOT / 'guide/comparison_r2.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    panels = json.loads(PANELS.read_text(encoding='utf-8'))['panels']
    OUT.mkdir(parents=True, exist_ok=True)
    assembly = cq.Assembly(name='r2_reference_NOT_FOR_PRODUCTION')
    parts = []
    previews = []
    z = cfg['alignment']['z_offset_mm']
    with tempfile.TemporaryDirectory() as tmp:
        for layer in cfg['layers']:
            boxes = [panels[k]['bbox'] for k in layer['panel_indices']]
            box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
            assert abs(box[2]-box[0]-286.4)<.001 and abs(box[3]-box[1]-95.8)<.001
            path = Path(tmp) / (layer['id']+'.dxf')
            subprocess.run([sys.executable, str(ROOT/'inspection/scripts/panel_to_dxf.py'), str(SOURCE), str(path),
                            *map(str,box), str(-box[0]), str(-box[1])], check=True, capture_output=True)
            wires = cq.importers.importDXF(str(path), tol=.01).wires().vals()
            thickness = layer['thickness_mm']
            if layer['id'] in ('P0','P1'):
                # The sheet nests loose hex washers inside its large opening. They are
                # not installed at the cutting-sheet coordinates. Exclude those islands;
                # boolean cuts also preserve holes intersecting the frame boundary.
                wires.sort(key=lambda w:cq.Face.makeFromWires(w).Area(), reverse=True)
                shape = cq.Solid.extrudeLinear(wires[0], [], (0,0,thickness))
                for wire in wires[1:]:
                    shape = shape.cut(cq.Solid.extrudeLinear(wire, [], (0,0,thickness)))
            else:
                shape = cq.Workplane('XY').newObject(wires).toPending().extrude(thickness).val()
            shape = shape.translate((*cfg['alignment']['xy_offset_mm'], z))
            if not shape.isValid() or shape.Volume() <= 0:
                raise ValueError(f"invalid reference solid: {layer['id']}")
            solids = len(shape.Solids())
            assert solids == layer['expected_solids'], (layer['id'], solids)
            bounds = shape.BoundingBox()
            assert abs(bounds.zlen-thickness)<1e-5
            filename = f"r2-{layer['id']}.stl"
            cq.exporters.export(shape, str(OUT/filename), tolerance=.03, angularTolerance=.15)
            assembly.add(shape, name=layer['id'], color=cq.Color(layer['color']))
            svg = cq.exporters.getSVG(shape, opts={'width':420,'height':160,'projectionDir':(0,0,1),'showAxes':False,'showHidden':False,'strokeWidth':.3})
            svg = svg[svg.index('<svg'):].replace('<svg ', f'<svg x="{(len(parts)%2)*450}" y="{(len(parts)//2)*200+30}" ', 1)
            previews.append(f'<text x="{(len(parts)%2)*450+20}" y="{(len(parts)//2)*200+25}" font-size="17">{layer["id"]} · {thickness} mm (nominal)</text>'+svg)
            parts.append(dict(id=layer['id'], label=layer['label'], color=layer['color'],
                thickness_mm=thickness, z_mm=z, solids=solids, volume_mm3=round(shape.Volume(),4),
                bbox=[[bounds.xmin,bounds.ymin,bounds.zmin],[bounds.xmax,bounds.ymax,bounds.zmax]],
                category='r2 비교용', reference=True, qty=solids, detail=layer['material'],
                explode_rank=len(parts), pieces=[dict(mesh='models/'+filename,bodies=[layer['id']])],
                mesh='models/'+filename, sha256=sha(OUT/filename)))
            z += thickness
    cq.exporters.export(assembly.toCompound(), str(OUT/'46es_r2_reference.step'))
    (OUT/'overview.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 640"><rect width="900" height="640" fill="#fff"/><g font-family="sans-serif">'+''.join(previews)+'</g><text x="20" y="630" font-family="sans-serif" font-size="14">r2 reference only · nominal thickness · stacking order assumed</text></svg>',encoding='utf-8')
    result = dict(schema_version=1, purpose='comparison_only_not_for_production',
        source_files={str(p.relative_to(ROOT)):sha(p) for p in (SOURCE,PANELS,CONFIG,Path(__file__).resolve(),ROOT/'inspection/scripts/panel_to_dxf.py',ROOT/'cad/46es_r2_keyboard.dwg')},
        alignment=cfg['alignment'], assumptions=cfg['assumptions'], repairs=cfg['repairs'],
        nominal_stack_mm=sum(x['thickness_mm'] for x in cfg['layers']), parts=parts,
        step_sha256=sha(OUT/'46es_r2_reference.step'))
    (OUT/'reference.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'layers':len(parts),'solids':sum(p['solids'] for p in parts),'valid':True,'nominal_stack_mm':result['nominal_stack_mm']},ensure_ascii=False))

if __name__ == '__main__':
    build()
