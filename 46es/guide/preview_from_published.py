#!/usr/bin/env python3
"""Build an explicitly labelled UI preview using hash-matched, already published assets.
No SolidCraft evaluation or new v5 rendering is claimed. Full publication uses build_guide.py.
Input folder needs assembly.json, models/, img/ from the existing published guide.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import zipfile
from PIL import Image
import assembly
import build_guide as guide

HERE=Path(__file__).resolve().parent

def build(source,out):
    spec=json.loads((HERE/'guide_v5.json').read_text(encoding='utf-8'))
    config=json.loads((HERE/spec['interactive']).read_text(encoding='utf-8'))
    model=HERE/spec['model']
    data=json.loads((source/'assembly.json').read_text(encoding='utf-8'))
    expected=hashlib.sha256(model.read_bytes()).hexdigest()
    if data['model_sha']!=expected:
        raise SystemExit('Published meshes are for a different CAD model; do not reuse.')
    with zipfile.ZipFile(model) as z: params=json.loads(z.read('document.json'))['params']
    numeric={}
    for p in params:
        m=re.fullmatch(r'([-+]?\d+(?:\.\d+)?)\s*(?:mm)?',p['expr'])
        if m:numeric[p['name']]=float(m[1])
    ctx=guide.Ctx(spec,dict(bodies=[],params=[dict(name=k,value=v) for k,v in numeric.items()]),[],{})
    section=next(s for s in spec['sections'] if s['type']=='assembly')
    old={s['id']:s for s in data['steps']}
    steps=[]
    for phase in section['phases']:
        for s in phase['steps']:
            steps.append(dict(old[s['id']],title=ctx.text(s['title']),phase=phase['title'],body=ctx.text(s.get('text','')),
                items=[ctx.text(x) for x in s.get('list',[])],check=ctx.text(s.get('check','')),fix=ctx.text(s.get('fix','')),**config['steps'][s['id']]))
    data['steps']=steps
    out.mkdir(parents=True,exist_ok=True)
    # Copy only referenced v5 meshes and image assets. Missing resources fail early.
    for part in data['parts']:
        for piece in part.get('pieces',[]):
            path=piece['mesh'];(out/path).parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source/path,out/path)
    for f in (source/'img').glob('*.png'):
        (out/'img').mkdir(exist_ok=True);shutil.copyfile(f,out/'img'/f.name)
        with Image.open(f) as im:ctx.sizes[f.stem]=im.size
    # Step diagrams are reused from the published build (diagrams.py needs the evaluated CAD bodies).
    published=[d for s in data['steps'] for d in s.get('diagrams',[])]
    wanted={g for ph in section['phases'] for s in ph['steps'] for g in s.get('diagrams',[])}
    ctx.diagrams={g:[d for d in published if re.fullmatch(rf'{re.escape(g)}(-\d+)?\.svg',Path(d['path']).name)] for g in wanted}
    missing=sorted(g for g in wanted if not ctx.diagrams[g])
    if missing:
        raise SystemExit(f'Published build has no diagrams for {missing}; rebuild with build_guide.py.')
    shutil.copytree(source/'img'/'diagrams',out/'img'/'diagrams',dirs_exist_ok=True)
    assembly.prepare_comparison(HERE,out,guide.die)
    from illustrations import prepare as draw_illustrations
    draw_illustrations(out, data)
    (out/'assembly.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    for name in ('assembly.js','viewer.js','assembly.css','comparison.js'):
        shutil.copyfile(HERE/'assets'/name,out/name)
    shutil.copytree(HERE/'assets/vendor',out/'vendor',dirs_exist_ok=True)
    css=(HERE/'assets/guide.css').read_text(encoding='utf-8')
    js=(HERE/'assets/guide.js').read_text(encoding='utf-8')
    full=guide.s_assembly(section,ctx)
    page=f'''<!doctype html><html lang="ko" data-theme="light" data-store="46es-guide-v5"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>46es 시각 조립서 · UI 검토본</title><style>{css}</style><link rel="stylesheet" href="assembly.css"></head><body><header class="wrap mast"><h1>46es 조립 가이드</h1><p class="sub">v5 · PSD60 Defender · 46키 핸드와이어드</p></header><main class="wrap">{assembly.markup(config)}<details id="reference-docs" class="reference-docs"><summary>전체 조립 설명 · 확인 목록</summary>{full}</details></main><footer class="wrap"><p>UI 검토본. v5 모델 해시 {expected[:12]}와 일치하는 게시 자산을 재사용했습니다. 새 CAD 평가·렌더를 수행한 정식 빌드는 아닙니다.</p></footer><script>{js}</script><script type="module" src="assembly.js"></script></body></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')
    print(f'UI preview: {out} · {len(steps)} steps · matching model {expected[:12]}')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--published',type=Path,required=True)
    ap.add_argument('--out',type=Path,default=HERE/'out_preview')
    a=ap.parse_args();build(a.published.resolve(),a.out.resolve())
