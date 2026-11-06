"""CAD-backed assets and data for the progressive assembly viewer."""
import hashlib
import json
import shutil
import struct
from pathlib import Path


def prepare(ctx, base, out, cli, model, model_sha, cache, expand, run, die):
    config = ctx.spec.get('interactive')
    if not config:
        return
    config = json.loads((base / config).read_text(encoding='utf-8'))
    ctx.interactive = config
    sections = ctx.spec['sections']
    source = next(s for s in sections if s['type'] == 'parts')
    assembly = next(s for s in sections if s['type'] == 'assembly')
    parts = []
    for p in source['printed']:
        parts.append(dict(id=p['bodies'][0], label=ctx.text(p['label']), qty=p.get('qty', 1),
                          category='출력 부품', detail=ctx.text(p.get('note', '')),
                          bodies=p['bodies']))
    for p in source['hardware']:
        parts.append(dict(id=p['id'], label=ctx.text(p['item']), qty=p['qty'], category='구매품',
                          detail=ctx.text(p['spec']) + ' · ' + ctx.text(p['decide']),
                          bodies=config['hardware_bodies'].get(p['id'], [])))
    for p in config['references']:
        parts.append(dict(p, category='참고 형상'))
    by_id = {p['id']: p for p in parts}
    if len(by_id) != len(parts):
        die('interactive: duplicate part ids')
    for p in parts:
        p['bodies'] = expand(p['bodies'], ctx.names, ctx.groups, p['id'])
        p['detail'] = p.get('detail', '')
        p['color'] = config.get('colors', {}).get(p['id'], '#87959f')
        p['reference'] = p['category'] == '참고 형상' or p['id'] in config.get('approximate', [])
        if p['reference']:
            p['detail'] += ' · 형상은 위치 확인용이며 실물과 다를 수 있습니다.'
        if p['bodies']:
            lo = [min(ctx.bodies[b]['bbox']['min'][i] for b in p['bodies']) for i in range(3)]
            hi = [max(ctx.bodies[b]['bbox']['max'][i] for b in p['bodies']) for i in range(3)]
            p['bbox'] = [lo, hi]
            p['size'] = ' × '.join(f'{hi[i]-lo[i]:.1f}' for i in range(3)) + ' mm'
    steps = []
    for phase in assembly['phases']:
        for st in phase['steps']:
            if st['id'] not in config['steps']:
                die(f"interactive: missing step {st['id']}")
            setting = config['steps'][st['id']]
            for pid in setting['show'] + setting['focus'] + list(setting['needs']):
                if pid not in by_id:
                    die(f'interactive: unknown part {pid}')
            if not set(setting['focus']) <= set(setting['show']):
                die(f"interactive: focus not visible in {st['id']}")
            steps.append(dict(id=st['id'], title=ctx.text(st['title']), phase=phase['title'],
                              body=ctx.text(st.get('text', '')),
                              items=[ctx.text(x) for x in st.get('list', [])],
                              check=ctx.text(st.get('check', '')), fix=ctx.text(st.get('fix', '')),
                              image='img/' + st.get('render', 'hero') + '.png', **setting))
    key = hashlib.sha256(json.dumps([model_sha, [(p['id'], p['bodies']) for p in parts], 2]).encode()).hexdigest()[:20]
    meshes = cache / 'web' / key
    meshes.mkdir(parents=True, exist_ok=True)
    commands = []
    exports = []
    for i, p in enumerate(parts):
        if not p['bodies']:
            continue
        p['pieces'] = []
        if p['id'] == 'switches':
            body_sets = [[b for b in p['bodies'] if b.startswith(prefixes)]
                         for prefixes in (('REF_MX_LOWER','REF_MX_GUIDE'), ('REF_MX_UPPER',), ('REF_MX_STEM',), ('REF_MX_CONTACT',))]
            body_sets = [b for b in body_sets if b]
        else:
            body_sets = [[b] for b in p['bodies']] if p['id'] in ('m2-5','m2-6','m2-nuts') else [p['bodies']]
        for j, bodies in enumerate(body_sets):
            filename = f'part-{i:02}-{j:02}.stl'
            piece = dict(mesh='models/' + filename, bodies=bodies)
            if p['id'] == 'switches':
                piece['color'] = ['#c8bc98','#e6dfca','#e8bd30','#be9456'][j]
            p['pieces'].append(piece)
            exports.append((p, piece))
            if not (meshes / filename).exists():
                commands.append(dict(command='file.export_stl', params=dict(
                    path=str(meshes / filename), bodies=bodies, quality='standard')))
        p['mesh'] = p['pieces'][0]['mesh']
    if commands:
        script = meshes / 'export.json'
        script.write_text(json.dumps(commands), encoding='utf-8')
        run([cli, 'run', script, '--in', model, '--quiet'])
    target = out / 'models'
    target.mkdir(parents=True, exist_ok=True)
    for p, piece in exports:
        path = meshes / Path(piece['mesh']).name
        raw = path.read_bytes()
        if len(raw) < 84 or len(raw) != 84 + 50 * struct.unpack_from('<I', raw, 80)[0]:
            die(f'interactive: invalid binary STL {path}')
        # Refuse stale print-oriented meshes: every vertex must stay in CAD world bounds.
        low, high = p['bbox']
        for offset in range(84, len(raw), 50):
            for v in struct.iter_unpack('<fff', raw[offset+12:offset+48]):
                if any(v[i] < low[i] - .1 or v[i] > high[i] + .1 for i in range(3)):
                    die(f"interactive: mesh outside CAD bounds: {p['id']}")
        shutil.copyfile(path, target / path.name)
    data = dict(parts=parts, steps=steps, model_sha=model_sha, tools=ctx.text(source.get('tools', '')))
    (out / 'assembly.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    for name in ('assembly.js', 'viewer.js', 'assembly.css'):
        shutil.copyfile(Path(__file__).parent / 'assets' / name, out / name)
    shutil.copytree(Path(__file__).parent / 'assets' / 'vendor', out / 'vendor', dirs_exist_ok=True)


DEFAULT_LABELS = dict(
    eyebrow='BUILD / 46es v4',
    case_hint='케이스는 부분 실측을 반영한 검토 형상입니다. 테두리 Z 14 / 커버 윗면 Z 15 mm(약 1 mm 돌출). 스위치·키캡은 MX·OEM 참고 형상이며 실물 치수는 미확정입니다. 배선은 3D 형상이 없습니다.')


def markup(config=None):
    labels = dict(DEFAULT_LABELS, **((config or {}).get('labels') or {}))
    return '''<section id="interactive" class="assembly-app" aria-label="3D 단계별 조립">
<div class="assembly-heading"><div><p class="eyebrow">''' + labels['eyebrow'] + '''</p><h2>한 단계씩, 직접 살펴보며 조립하기</h2></div><a href="#assembly">전체 조립 설명 ↓</a></div>
<p>이번 작업의 부품은 주황색으로 강조됩니다. 부품 카드를 누르면 해당 부품을 찾아볼 수 있습니다.</p>
<p id="assembly-status" role="status">조립 가이드를 불러오는 중입니다. 아래 이미지와 전체 조립 설명도 이용할 수 있습니다.</p>
<div id="assembly-ui" hidden>
<div class="assembly-nav"><button id="asm-prev" type="button">← 이전</button><label>단계 <select id="asm-step"></select></label><button id="asm-next" type="button">다음 →</button></div>
<div class="assembly-layout"><div class="assembly-visual"><div id="asm-canvas" tabindex="0" aria-label="3D 조립 모델. 드래그로 회전, 휠 또는 두 손가락으로 확대"></div>
<div class="assembly-toolbar"><button type="button" data-view="iso">추천 시점</button><button type="button" data-view="top">위</button><button type="button" data-view="bottom">아래</button><button type="button" data-view="front">앞 높이</button><label>분해 <input id="asm-explode" type="range" min="0" max="1" step="0.01" value="0"></label></div>
<p class="assembly-hint">드래그: 회전 · 휠/핀치: 확대 · 오른쪽 드래그: 이동</p>
<p class="assembly-hint">''' + labels['case_hint'] + '''</p>
<p id="asm-picked" aria-live="polite"></p>
<details id="asm-fallback"><summary>이 단계의 참고 이미지</summary><img id="asm-image" alt="현재 조립 단계 참고 이미지"></details></div>
<article class="assembly-instruction" aria-live="polite"><p id="asm-phase" class="eyebrow"></p><h3 id="asm-title"></h3><div id="asm-body"></div><div id="asm-check" class="assembly-check"></div><div id="asm-fix"></div><label class="tick"><input type="checkbox" id="asm-done"> 이 단계 완료</label><p id="asm-progress"></p><a id="asm-detail">전체 설명에서 보기 ↗</a></article></div>
<div class="assembly-parts-head"><h3>준비할 부품</h3><label>목록 <select id="asm-scope"><option value="step">현재 단계</option><option value="all">전체 부품</option></select></label><label>검색 <input id="asm-search" type="search" placeholder="이름 또는 규격"></label></div>
<p id="asm-parts-note"></p><div id="asm-parts" class="assembly-parts"></div><p id="asm-tools" class="note"></p>
</div><noscript><p>3D 조립 화면은 JavaScript가 필요합니다. 아래 조립 순서와 이미지를 이용하세요.</p></noscript></section>'''
