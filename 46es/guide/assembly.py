"""CAD-backed assets and metadata for the 46es v5 technical motion 3D assembly guide."""
import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np

import diagrams
import glb

VENDOR_FILES = (
    'three.module.js',
    'three.core.js',
    'GLTFLoader.js',
    'BufferGeometryUtils.js',
    'LICENSE',
)


def _body_center(box):
    return [round((box['min'][i] + box['max'][i]) / 2, 3) for i in range(3)]


def _export_keys_and_pads(ctx, base):
    """Export 46 switch positions/pins/matrix roles and 16 Pro Micro signal pads from CAD sources."""
    import ctrl_v5
    from mounts_v5 import MX_CONTACTS, MX_PIN_DEPTH_FROM_SEAT

    key_rows, pins_spec, role_map = diagrams.load(ctx)
    upper_t = float(ctx.params.get('TBD_upper_plate_T', 1.7))
    seat_z = round(13.0 - upper_t, 4)
    pin_tip_z = round(seat_z - MX_PIN_DEPTH_FROM_SEAT, 4)

    # OEM row lookup matching tools/build_assembly_reference_v5.py
    oem_rows = {
        2: {3, 6, 9, 11, 14, 17, 25, 28, 31, 33, 36, 39, 18},
        3: {2, 5, 8, 10, 13, 16, 24, 27, 30, 32, 35, 38},
        4: {1, 4, 7, 12, 15, 23, 26, 29, 34, 37, 43},
        1: {19},
    }
    keys_out = []
    for k in key_rows:
        rad = math.radians(k['rot'])
        ca, sa = math.cos(rad), math.sin(rad)
        contact_xy = [
            [round(k['x'] + ox * ca - oy * sa, 3), round(k['y'] + ox * sa + oy * ca, 3)]
            for ox, oy in MX_CONTACTS
        ]
        oem_row = next((r for r, ids in oem_rows.items() if k['n'] in ids), 5)
        keys_out.append(dict(
            id=k['n'],
            x=round(k['x'], 3),
            y=round(k['y'], 3),
            seat_z=seat_z,
            pin_tip_z=pin_tip_z,
            rot=round(k['rot'], 3),
            w_u=k['w'],
            oem_row=oem_row,
            row=k['row'],
            col=k['col'],
            legend=k['legend'],
            pins=contact_xy,
        ))

    solder_z = round(ctrl_v5.PCB_Z + ctrl_v5.PCB_T, 4)
    pads_out = []
    for pad in diagrams.pad_table(role_map):
        if pad['role']:
            pads_out.append(dict(
                name=pad['name'],
                role=pad['role'],
                header=pad['header'],
                pin=pad['n'],
                x=round(pad['x'], 3),
                y=round(pad['y'], 3),
                z=solder_z,
            ))

    spine_box = ctx.bodies['PLATE_SPINE_V1']['bbox']
    plates = [ctx.bodies[n]['bbox'] for n in ('PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1')]
    seam_x = round(float(ctx.params.get('split_center_X', (plates[0]['max'][0] + plates[1]['min'][0]) / 2)), 3)
    spine_grooves = dict(
        x_min=round(spine_box['min'][0], 3),
        x_max=round(spine_box['max'][0], 3),
        ys=list(diagrams.SPINE_GROOVES_Y),
        z=round(float(ctx.params.get('split_spine_bottom_Z', 3.05)) + 0.9, 3),
        seam_x=seam_x,
    )
    return keys_out, pads_out, spine_grooves, pins_spec


def prepare(ctx, base, out, cli, model, model_sha, cache, expand, run, die, assembly_only=False):
    config_rel = ctx.spec.get('interactive')
    if not config_rel:
        return
    config = json.loads((base / config_rel).read_text(encoding='utf-8'))
    ctx.interactive = config

    sections = ctx.spec['sections']
    source = next(s for s in sections if s['type'] == 'parts')
    excluded = set(config.get('exclude_from_scene', []))
    hw_labels_override = config.get('hardware_labels', {})
    hw_by_id = {h['id']: h for h in source['hardware']}

    parts = []
    for p in source['printed']:
        pid = p['bodies'][0]
        if pid in excluded:
            continue
        parts.append(dict(
            id=pid,
            label=ctx.text(p['label']),
            category='printed',
            bodies=list(p['bodies']),
        ))
    for pid, patterns in config['hardware_bodies'].items():
        hw = hw_by_id.get(pid)
        label = hw_labels_override.get(pid) or (ctx.text(hw['item']) if hw else pid)
        parts.append(dict(
            id=pid,
            label=label,
            category='hardware',
            bodies=list(patterns),
        ))
    for p in config.get('references', []):
        parts.append(dict(
            id=p['id'],
            label=p['label'],
            category='reference',
            bodies=list(p['bodies']),
        ))

    by_id = {p['id']: p for p in parts}
    if len(by_id) != len(parts):
        die('interactive: duplicate part ids')

    procedural = set(config.get('procedural_parts', []))
    steps = config['steps']
    group_by_part = {}
    for step in steps:
        for pid in step['parts']:
            if pid not in by_id and pid not in procedural:
                die(f"interactive: unknown part {pid} in {step['id']}")
            group_by_part[pid] = step['code']

    keys_out, pads_out, spine_grooves, pins_spec = _export_keys_and_pads(ctx, base)

    for p in parts:
        p['bodies'] = expand(p['bodies'], ctx.names, ctx.groups, p['id'])
        p['group'] = group_by_part.get(p['id'], '')
        p['color'] = config.get('colors', {}).get(p['id'], '#87959f')
        p['fastener'] = p['id'] in set(config.get('fastener_parts', []))
        if p['bodies']:
            lo = [min(ctx.bodies[b]['bbox']['min'][i] for b in p['bodies']) for i in range(3)]
            hi = [max(ctx.bodies[b]['bbox']['max'][i] for b in p['bodies']) for i in range(3)]
            p['bbox'] = [[round(v, 3) for v in lo], [round(v, 3) for v in hi]]
            p['size'] = ' × '.join(f'{hi[i] - lo[i]:.1f}' for i in range(3)) + ' mm'
            p['body_centers'] = [_body_center(ctx.bodies[b]['bbox']) for b in p['bodies']]
        if p['id'] in ('housing', 'controller'):
            p['instance_count'] = 1
        elif p['id'] in ('switches', 'keycaps'):
            p['instance_count'] = len(keys_out)
        else:
            p['instance_count'] = len(p['bodies'])

    piece_colors = config.get('piece_colors', {})
    cache_key = hashlib.sha256(json.dumps(
        [model_sha, [(p['id'], p['bodies']) for p in parts], piece_colors, 3]
    ).encode()).hexdigest()[:20]
    meshes = cache / 'web' / cache_key
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
            body_sets = [
                [b for b in p['bodies'] if b.startswith(prefixes)]
                for prefixes in (('REF_MX_LOWER', 'REF_MX_GUIDE'), ('REF_MX_UPPER',), ('REF_MX_STEM',), ('REF_MX_CONTACT',))
            ]
            body_sets = [b for b in body_sets if b]
        else:
            body_sets = [p['bodies']]
        for j, bodies in enumerate(body_sets):
            filename = f'part-{i:02}-{j:02}.stl'
            piece = dict(
                mesh=f'models/assembly.glb#{Path(filename).stem}',
                bodies=bodies,
                instances=instances([ctx.bodies[b]['bbox'] for b in bodies]),
            )
            if colors:
                piece['color'] = list(colors.values())[j]
            elif p['id'] == 'switches':
                piece['role'] = ['lower', 'upper', 'stem', 'contact'][j]
                piece['color'] = ['#c8bc98', '#e6dfca', '#e8bd30', '#be9456'][j]
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

    loaded = []
    for p, piece in exports:
        name = piece['mesh'].split('#')[1]
        try:
            tris = glb.read_stl(meshes / f'{name}.stl')
        except ValueError as e:
            die(f'interactive: {e}')
        low, high = np.array(p['bbox'][0]), np.array(p['bbox'][1])
        if (tris < low - 0.1).any() or (tris > high + 0.1).any():
            die(f"interactive: mesh outside CAD bounds: {p['id']}")
        loaded.append((name, tris))

    (out / 'models').mkdir(parents=True, exist_ok=True)
    for stale in (out / 'models').glob('part-*.stl'):
        stale.unlink()
    for stale in (out / 'models').glob('r2*'):
        stale.unlink()
    glb_path = out / 'models' / 'assembly.glb'
    glb.write(glb_path, loaded)

    data = dict(
        schema_version=config['schema_version'],
        duration_sec=config['duration_sec'],
        closeup_key_id=config['closeup_key_id'],
        tilt_source=config['tilt_source'],
        steps=steps,
        bom_groups=config['bom_groups'],
        parts=parts,
        keys=keys_out,
        controller_pads=pads_out,
        spine_grooves=spine_grooves,
        matrix_pins=pins_spec,
        model_sha=model_sha,
        model_bytes=glb_path.stat().st_size,
    )
    (out / 'assembly.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8', newline='\n')
    copy_assets(out)


def copy_assets(out):
    """Copy motion engine modules, stylesheet, and vendored Three.js runtime (no OrbitControls)."""
    assets_root = Path(__file__).parent / 'assets'
    motion_dst = out / 'motion'
    if motion_dst.exists():
        shutil.rmtree(motion_dst)
    shutil.copytree(assets_root / 'motion', motion_dst)

    vendor_dst = out / 'vendor'
    vendor_dst.mkdir(parents=True, exist_ok=True)
    for stale in vendor_dst.iterdir():
        if stale.name not in VENDOR_FILES:
            stale.unlink() if stale.is_file() else shutil.rmtree(stale)
    for name in VENDOR_FILES:
        shutil.copyfile(assets_root / 'vendor' / name, vendor_dst / name)


def instances(boxes, gap=0.2):
    """Group CAD body boxes that share one plan-view spot into one physical instance each."""
    inside = lambda c, b: all(b['min'][i] - gap <= c[i] <= b['max'][i] + gap for i in (0, 1))
    centre = lambda b: [(b['min'][i] + b['max'][i]) / 2 for i in range(3)]
    groups = []
    for box in boxes:
        group = next((g for g in groups if inside(centre(box), g[0]) or inside(centre(g[0]), box)), None)
        if group is None:
            groups.append([box, list(box['min']), list(box['max']), 1])
        else:
            group[1] = [min(group[1][i], box['min'][i]) for i in range(3)]
            group[2] = [max(group[2][i], box['max'][i]) for i in range(3)]
            group[3] += 1
    groups.sort(key=lambda g: (round(g[1][1]), g[1][0]))
    return [[[round(v, 2) for v in g[1]], [round(v, 2) for v in g[2]]] + ([g[3]] if g[3] > 1 else [])
            for g in groups]


def markup(config=None, fallback_hero='img/hero.png'):
    steps = (config or {}).get('steps', [])
    step_buttons = ''.join(
        f'<button type="button" class="step-btn" data-step="{idx}" aria-pressed="false" '
        f'title="{s["code"]} · {s["label"]}">STEP {idx}</button>'
        for idx, s in enumerate(steps, 1)
    )
    hero_html = (
        f'<img id="motion-fallback-img" src="{fallback_hero}" alt="46es v5 assembly">'
        if fallback_hero else ''
    )
    return f'''<section id="motion-stage" class="motion-stage" aria-label="46es v5 3D Technical Assembly Guide">
  <div class="stage-frame" id="stage-frame">
    <div id="motion-canvas" class="motion-canvas" aria-label="46es v5 3D isometric assembly canvas"></div>
    <svg id="motion-overlay" class="motion-overlay" viewBox="0 0 1920 1080" preserveAspectRatio="none" aria-hidden="true"></svg>
    <div class="stage-header" aria-hidden="true">
      <div class="brand-tag"><span class="brand-code">46ES-V5</span><span class="brand-sep">/</span><span id="hud-phase-code" class="phase-code">01 · DIM + EXPLODE</span></div>
      <div id="hud-telemetry" class="hud-telemetry" hidden></div>
      <div class="time-readout"><span id="hud-time-big">00.0</span><span class="unit">s</span><span class="time-total">/ 32.0s</span></div>
    </div>
    <div id="hud-bom" class="hud-bom" hidden aria-label="BOM inventory grid">
      <div class="bom-head"><span class="bom-title">BOM</span><span id="bom-total-badge" class="bom-total">0 pcs</span></div>
      <div id="bom-grid" class="bom-grid"></div>
    </div>
    <div id="hud-report" class="hud-report" hidden aria-label="Build verification report">
      <div class="rep-cell"><span class="rep-k">PARTS</span><strong id="rep-parts" class="rep-v">0</strong><span class="rep-u">pcs</span></div>
      <div class="rep-cell"><span class="rep-k">STEPS</span><strong id="rep-steps" class="rep-v">0</strong><span class="rep-u">seq</span></div>
      <div class="rep-cell"><span class="rep-k">GROUPS</span><strong id="rep-groups" class="rep-v">0</strong><span class="rep-u">grp</span></div>
      <div class="rep-cell"><span class="rep-k">CYCLE</span><strong id="rep-time" class="rep-v">0.0</strong><span class="rep-u">s</span></div>
      <div class="rep-cell rep-ok"><span class="rep-k">SHORT</span><strong id="rep-short" class="rep-v">0</strong><span class="rep-u">err</span></div>
      <div class="rep-cell rep-ok"><span class="rep-k">GAP</span><strong id="rep-gap" class="rep-v">0 ✓</strong><span class="rep-u">mm</span></div>
    </div>
    <div id="motion-loading" class="motion-loading" role="status"><span class="load-code">46ES-V5</span><span id="motion-status-text">LOADING CAD</span></div>
    <div id="motion-fallback" class="motion-fallback" hidden>
      {hero_html}
      <div class="fallback-badge">WEBGL UNAVAILABLE · STATIC CAD FALLBACK</div>
    </div>
  </div>
  <div class="control-bar" role="region" aria-label="Sequence controls">
    <button id="btn-play" class="ctrl-play" type="button" aria-label="Play or pause" aria-pressed="false">▶</button>
    <div class="scrubber-wrap">
      <input id="timeline-scrubber" class="scrubber" type="range" min="0" max="32" step="0.05" value="0" aria-label="Timeline scrubber (seconds)">
      <div class="phase-ticks" aria-hidden="true">
        <span style="left:0%">0s</span>
        <span style="left:21.875%">7s</span>
        <span style="left:40.625%">13s</span>
        <span style="left:53.125%">17s</span>
        <span style="left:71.875%">23s</span>
        <span style="left:90.625%">29s</span>
        <span style="left:100%">32s</span>
      </div>
    </div>
    <span id="ctrl-time" class="ctrl-time">00.0s</span>
    <div class="step-toggles" role="group" aria-label="Manual assembly steps">{step_buttons}</div>
  </div>
</section>'''
