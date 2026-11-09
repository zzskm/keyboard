"""CAD-backed assets and data for the progressive assembly viewer."""
import hashlib
import json
import shutil
import struct
from pathlib import Path


def prepare(ctx, base, out, cli, model, model_sha, cache, expand, run, die, assembly_only=False):
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
                              diagrams=[d for gid in st.get('diagrams', []) for d in ctx.diagrams[gid]],
                              image='img/' + st.get('render', 'hero') + '.png', **setting))
    piece_colors = config.get('piece_colors', {})
    key = hashlib.sha256(json.dumps([model_sha, [(p['id'], p['bodies']) for p in parts],
                                     piece_colors, 2]).encode()).hexdigest()[:20]
    meshes = cache / 'web' / key
    meshes.mkdir(parents=True, exist_ok=True)
    commands = []
    exports = []
    for i, p in enumerate(parts):
        if not p['bodies']:
            continue
        p['pieces'] = []
        colors = piece_colors.get(p['id'], {})
        if colors:
            body_sets = [expand([pattern], ctx.names, ctx.groups, p['id']) for pattern in colors]
            assigned = [body for group in body_sets for body in group]
            if sorted(assigned) != sorted(p['bodies']):
                die(f"interactive: invalid color groups for {p['id']}")
            p['preserveColors'] = True
        elif p['id'] == 'switches':
            body_sets = [[b for b in p['bodies'] if b.startswith(prefixes)]
                         for prefixes in (('REF_MX_LOWER','REF_MX_GUIDE'), ('REF_MX_UPPER',), ('REF_MX_STEM',), ('REF_MX_CONTACT',))]
            body_sets = [b for b in body_sets if b]
        else:
            body_sets = [[b] for b in p['bodies']] if p['id'] in ('m2-5','m2-6','m2-nuts') else [p['bodies']]
        for j, bodies in enumerate(body_sets):
            filename = f'part-{i:02}-{j:02}.stl'
            piece = dict(mesh='models/' + filename, bodies=bodies)
            if colors:
                piece['color'] = list(colors.values())[j]
            elif p['id'] == 'switches':
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
    prepare_comparison(base, out, die)
    from illustrations import prepare as draw_illustrations
    draw_illustrations(out, data)
    if assembly_only:
        for step in steps:
            step['image'] = step['illustration']
    (out / 'assembly.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    for name in ('assembly.js', 'viewer.js', 'assembly.css', 'comparison.js'):
        shutil.copyfile(Path(__file__).parent / 'assets' / name, out / name)
    shutil.copytree(Path(__file__).parent / 'assets' / 'vendor', out / 'vendor', dirs_exist_ok=True)


def prepare_comparison(base, out, die):
    root = base.parent
    folder = root / 'model/reference_r2'
    manifest = folder / 'reference.json'
    if not manifest.exists():
        die('r2 reference missing: run python 46es/tools/build_r2_reference.py')
    ref = json.loads(manifest.read_text(encoding='utf-8'))
    for path, expected in ref['source_files'].items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            die('r2 reference stale: run python 46es/tools/build_r2_reference.py')
    for p in ref['parts']:
        src = folder / Path(p['mesh']).name
        if hashlib.sha256(src.read_bytes()).hexdigest() != p['sha256']:
            die('r2 reference mesh hash mismatch: ' + p['id'])
        (out / 'models').mkdir(exist_ok=True, parents=True)
        shutil.copyfile(src, out / p['mesh'])
    step = folder / '46es_r2_reference.step'
    if hashlib.sha256(step.read_bytes()).hexdigest() != ref['step_sha256']:
        die('r2 reference STEP hash mismatch')
    shutil.copyfile(step, out / step.name)
    shutil.copyfile(manifest, out / 'r2-reference.json')
    shutil.copyfile(folder / 'overview.svg', out / 'r2-overview.svg')


DEFAULT_LABELS = dict(
    eyebrow='BUILD / 46es v5',
    case_hint='케이스는 부분 실측을 반영한 검토 형상입니다. 테두리 Z 14 / 커버 윗면 Z 15 mm(약 1 mm 돌출). 스위치·키캡은 MX·OEM 참고 형상이며 실물 치수는 미확정입니다. 배선은 3D 형상이 없고 배선 단계의 그림으로 보여 줍니다.')


def markup(config=None):
    return '''<section id="interactive" class="assembly-app" aria-label="46es 시각 조립서">
<div class="build-heading"><div><p class="eyebrow">46es / BUILD BOOK</p><h2>부품을 보고, 한 단계씩.</h2></div><span class="build-badge">v5 · 시험 출력 전</span></div>
<div class="build-modes" role="group" aria-label="가이드 모드"><button id="mode-build" aria-pressed="true">조립하기</button><button id="mode-compare" aria-pressed="false">r2와 비교</button><a href="#reference-docs">상세 자료 ↗</a></div>
<p id="assembly-status" role="status">조립서를 불러오는 중입니다. 아래 전체 설명도 이용할 수 있습니다.</p>
<div id="assembly-ui" hidden>
<div id="build-panel">
<div class="assembly-nav"><button id="asm-prev" type="button" aria-label="이전 조립 단계">←</button><label><span class="sr-only">조립 단계</span><select id="asm-step"></select></label><button id="asm-next" type="button" aria-label="다음 조립 단계">→</button></div>
<div id="asm-phases" class="phase-track" aria-label="조립 구간"></div>
<div class="build-sheet">
<div class="build-step-heading"><span id="asm-number" class="build-number">01</span><div><p id="asm-phase" class="eyebrow"></p><h3 id="asm-title"></h3></div><span id="asm-progress"></span></div>
<div class="parts-tray"><div class="tray-label">이번에 사용할 부품 <span>3D에서 위치 표시</span></div><div id="asm-tray" class="tray-items"></div></div>
<div class="assembly-layout"><div class="assembly-visual"><div class="visual-key"><span><i class="old-dot"></i>앞 단계 / 주변 부품</span><span><i class="new-dot"></i>이번 작업</span></div><img id="asm-drawing" alt="현재 단계 조립도"><div id="asm-canvas" hidden tabindex="0" aria-label="3D 조립 모델. 드래그로 회전, 휠 또는 두 손가락으로 확대"></div>
<div class="assembly-toolbar"><button id="asm-installed" type="button" hidden>장착 후 보기</button><button id="asm-3d" type="button">3D로 보기</button><div id="asm-3d-tools" hidden><button type="button" data-view="reset">시점 복원</button><button type="button" data-view="iso">입체</button><button type="button" data-view="top">위</button><button type="button" data-view="bottom">아래</button><button type="button" data-view="front">앞</button><button id="asm-focus" type="button" aria-pressed="false">작업 부품만</button><label>분해 <input id="asm-explode" aria-label="조립 분해 정도" type="range" min="0" max="1" step="0.01" value="0"></label></div></div>
<p id="asm-picked" aria-live="polite"></p><details id="asm-fallback"><summary>참고 이미지 보기</summary><img id="asm-image" alt="현재 조립 단계 참고 이미지"></details></div>
<article class="assembly-instruction"><ol id="asm-actions" class="action-list"></ol><div id="asm-check" class="assembly-check"></div><details id="asm-details"><summary>세부 설명 · 안 맞을 때</summary><div id="asm-body"></div><div id="asm-fix"></div><a id="asm-detail">전체 설명에서 보기 ↗</a></details><label class="tick"><input type="checkbox" id="asm-done"> 이 단계 확인 완료</label><button id="asm-complete-next" class="primary-button" type="button">완료하고 다음 →</button></article></div>
<section id="asm-diagrams" class="step-diagrams" aria-label="이번 단계 그림" hidden></section>
</div>
<details class="parts-catalog"><summary>전체 부품 · 준비 체크 · 검색</summary><div class="assembly-parts-head"><label>목록 <select id="asm-scope"><option value="step">현재 단계</option><option value="all">전체 부품</option></select></label><label>검색 <input id="asm-search" type="search" placeholder="이름 또는 규격"></label></div><p id="asm-parts-note"></p><div id="asm-parts" class="assembly-parts"></div><p id="asm-tools" class="note"></p></details>
<p class="reference-note">케이스·스위치·키캡·구매품은 참고 형상입니다. 배선은 3D 대신 배선 단계의 그림으로 보여 줍니다. 분해 간격과 화살표는 조립 설명용이며 실물 끼움·공차를 보증하지 않습니다.</p>
</div>
<div id="compare-panel" hidden>
<div class="compare-heading"><div><p class="eyebrow">r2 ACRYLIC → v5 PRINTED</p><h3>무엇이 달라졌을까?</h3></div><span class="build-badge">같은 시점 · 같은 축척</span></div>
<p class="reference-note">r2는 도면 윤곽을 복원한 비교용 모델입니다. 두께는 공칭값, 아래→위 P0→P5 적층과 설치 높이는 가정입니다. 제작용으로 쓰지 마세요.</p>
<div class="compare-toolbar"><label>비교 대상 <select id="cmp-scope"><option value="all">전체 구조</option><option value="plate">스위치 판</option><option value="cover">커버</option></select></label><button id="cmp-3d" type="button">3D로 보기</button><div id="cmp-3d-tools" hidden><button data-compare-view="iso">입체</button><button data-compare-view="top">위</button><button data-compare-view="front">앞</button><label>분해 <input id="cmp-explode" aria-label="비교 모델 분해 정도" type="range" min="0" max="1" step="0.01" value="0.35"></label></div></div>
<p id="compare-status" role="status">비교 모델을 준비하고 있습니다.</p>
<div class="compare-grid"><article><h4>r2 <small>아크릴 · 6종 / 10조각</small></h4><div id="r2-canvas" class="compare-canvas" hidden aria-label="r2 비교 모델"></div><img id="r2-fallback" src="img/build/r2-all.png" alt="r2 아크릴 적층 조립도"><div id="r2-layers" class="layer-list"></div></article><article><h4>v5 <small>현행 · 분리형 plate + 자석 커버</small></h4><div id="v5-canvas" class="compare-canvas" hidden aria-label="v5 비교 모델"></div><img id="v5-fallback" src="img/build/v5-all.png" alt="현행 v5 분해 조립도"><p>좌우 plate는 mount 받침 7곳에 놓입니다. 평면 커버는 L·T·R을 개별 탈착합니다.</p></article></div>
<div class="compare-facts"><div><b>46개 키 위치</b><span>r2의 2D 키 배열이 기준</span></div><div><b>plate 구조</b><span>r2 1.5T 판 → v5 좌우 분할·국부 걸쇠 층</span></div><div><b>커버 유지보수</b><span>r2 적층 판 → v5 자석 탈착 3조각</span></div></div>
<details><summary>복원 근거와 가정 · 모델 내려받기</summary><ul id="r2-assumptions"></ul><p>좌표는 r2 P2 윗면과 v5 스위치 착좌면을 맞춘 비교 기준입니다. 하우징 설치 높이 비교가 아닙니다.</p><a href="46es_r2_reference.step" download>r2 비교용 STEP</a> · <a href="r2-reference.json">복원 근거와 파일 해시</a></details>
</div></div><noscript><p>시각 조립서는 JavaScript가 필요합니다. 아래 전체 조립 순서와 이미지를 이용하세요.</p></noscript></section>'''
