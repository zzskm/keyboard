"""CAD-backed assets and metadata for the 46es v5 technical motion 3D assembly guide."""
import hashlib
import json
import math
import re
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


def _fastener_trace_id(prefix, body_name, idx):
    """Deterministic human-readable CAD trace ID for each of the 42 physical fasteners."""
    m = re.search(r'(SO\d+|H0\d|LEGMAG_[LR]_(?:COVER|PLATE)|PLATE_\d+|SEAM_FRONT)', body_name)
    if m:
        tag = m.group(1).replace('_', '-')
        return f'{prefix}-{tag}'
    return f'{prefix}-{idx:02d}'


def _load_cad_verification(base, model_sha, closeup_key_id, die):
    """Read hash-verified CAD clearance & overlap measurements from inspection/data/."""
    verif_path = (base.parent / 'inspection' / 'data' / 'assembly-reference-v5-verification.json').resolve()
    if not verif_path.is_file():
        die(f'interactive: missing CAD verification record: {verif_path}')
    verif = json.loads(verif_path.read_text(encoding='utf-8-sig'))
    if verif.get('model_sha') != model_sha:
        die('interactive: assembly-reference-v5-verification.json model_sha differs from current CAD model')

    pin_dists = [
        float(m['min_distance_mm'])
        for m in verif.get('mount_switch_pin_fit', {}).get('mounts', {}).values()
        if m.get('min_distance_mm') is not None
    ]
    pin_min = round(min(pin_dists), 2) if pin_dists else None

    kc_pressed = verif.get('keycap', {}).get('pressed_4mm', {})
    cap_cover_min = round(float(kc_pressed.get('cover_min_mm', 0.0)), 2)
    cap_plate_min = round(float(verif.get('pressed_vs_plate', {}).get('min_distance_mm', 0.0)), 2)
    bracket_pairs = verif.get('controller', {}).get('bracket_switch_case_min', [])
    bracket_min = round(float(bracket_pairs[0][0]), 2) if bracket_pairs else None

    overlaps = (
        int(verif.get('mount_review_fit', {}).get('overlaps', 0))
        + int(verif.get('controller', {}).get('bracket_overlap_count', 0))
        + int(verif.get('pressed_vs_plate', {}).get('overlapping_caps', 0))
    )

    closeup_cover_mm = cap_cover_min
    closeup_cover_part = ''
    for entry in kc_pressed.get('closest', []):
        if int(entry[0]) == int(closeup_key_id):
            closeup_cover_mm = round(float(entry[1]), 2)
            closeup_cover_part = str(entry[2])
            break

    return dict(
        ok=bool(verif.get('ok', False)),
        overlaps=overlaps,
        pin_min_mm=pin_min,
        cap_cover_min_mm=cap_cover_min,
        cap_plate_min_mm=cap_plate_min,
        bracket_min_mm=bracket_min,
        closeup_key_cover_min_mm=closeup_cover_mm,
        closeup_key_cover_part=closeup_cover_part,
        model_sha_prefix=model_sha[:12],
    )


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
    non_countable = set(config.get('non_countable_parts', []))
    fastener_specs = config.get('fastener_specs', {})
    hw_labels_override = config.get('hardware_labels', {})
    hw_by_id = {h['id']: h for h in source['hardware']}

    parts = []
    for p in source['printed']:
        pid = p['bodies'][0]
        if pid in excluded:
            continue
        material = 'SLA 8001 Resin' if pid.startswith('COVER_') else 'MJF PA12'
        parts.append(dict(
            id=pid,
            label=ctx.text(p['label']),
            category='printed',
            material=material,
            unique_stl_count=1,
            bodies=list(p['bodies']),
        ))
    for pid, patterns in config['hardware_bodies'].items():
        hw = hw_by_id.get(pid)
        label = hw_labels_override.get(pid) or (ctx.text(hw['item']) if hw else pid)
        parts.append(dict(
            id=pid,
            label=label,
            category='hardware',
            material='Hardware',
            unique_stl_count=0,
            bodies=list(patterns),
        ))
    for p in config.get('references', []):
        parts.append(dict(
            id=p['id'],
            label=p['label'],
            category='reference',
            material='CNC Aluminum',
            unique_stl_count=0,
            bodies=list(p['bodies']),
        ))

    by_id = {p['id']: p for p in parts}
    if len(by_id) != len(parts):
        die('interactive: duplicate part ids')

    procedural = set(config.get('procedural_parts', []))
    steps = config['steps']
    group_by_part = {}
    step_num_by_part = {}
    for idx, step in enumerate(steps, 1):
        for pid in step['parts']:
            if pid not in by_id and pid not in procedural:
                die(f"interactive: unknown part {pid} in {step['id']}")
            group_by_part[pid] = step['code']
            step_num_by_part[pid] = idx

    layers = config.get('visibility_layers', [])
    layer_by_part = {}
    for layer in layers:
        for pid in layer['parts']:
            if pid in layer_by_part:
                die(f"interactive: part {pid} assigned to multiple visibility_layers")
            layer_by_part[pid] = layer['id']

    keys_out, pads_out, spine_grooves, pins_spec = _export_keys_and_pads(ctx, base)
    cad_verification = _load_cad_verification(base, model_sha, config['closeup_key_id'], die)

    fastener_instances = []
    for p in parts:
        p['bodies'] = expand(p['bodies'], ctx.names, ctx.groups, p['id'])
        p['group'] = group_by_part.get(p['id'], '')
        p['step'] = step_num_by_part.get(p['id'], 0)
        p['layer'] = layer_by_part.get(p['id'], '')
        p['countable'] = p['id'] not in non_countable
        p['color'] = config.get('colors', {}).get(p['id'], '#87959f')
        p['fastener'] = p['id'] in set(config.get('fastener_parts', []))
        if p['bodies']:
            lo = [min(ctx.bodies[b]['bbox']['min'][i] for b in p['bodies']) for i in range(3)]
            hi = [max(ctx.bodies[b]['bbox']['max'][i] for b in p['bodies']) for i in range(3)]
            p['bbox'] = [[round(v, 3) for v in lo], [round(v, 3) for v in hi]]
            p['size'] = ' × '.join(f'{hi[i] - lo[i]:.1f}' for i in range(3)) + ' mm'
            p['body_centers'] = [_body_center(ctx.bodies[b]['bbox']) for b in p['bodies']]
            p['volume_cm3'] = round(sum(float(ctx.bodies[b].get('volume_mm3', 0.0)) for b in p['bodies']) / 1000.0, 2)
            p['body_meta'] = {
                b: dict(
                    bbox=[
                        [round(v, 3) for v in ctx.bodies[b]['bbox']['min']],
                        [round(v, 3) for v in ctx.bodies[b]['bbox']['max']],
                    ],
                    center=_body_center(ctx.bodies[b]['bbox']),
                    volume_cm3=round(float(ctx.bodies[b].get('volume_mm3', 0.0)) / 1000.0, 3),
                )
                for b in p['bodies']
            }
        else:
            p['volume_cm3'] = 0.0
            p['body_meta'] = {}
        if not p['countable']:
            p['instance_count'] = 0
        elif p['id'] in ('housing', 'controller'):
            p['instance_count'] = 1
        elif p['id'] in ('switches', 'keycaps'):
            p['instance_count'] = len(keys_out)
        else:
            p['instance_count'] = len(p['bodies'])

        if p['fastener']:
            fspec = fastener_specs.get(p['id'])
            if not fspec:
                die(f"interactive: missing fastener_specs entry for {p['id']}")
            p['spec_label'] = fspec['spec_label']
            p['standard'] = fspec['standard']
            for f_idx, bname in enumerate(p['bodies'], 1):
                bmeta = p['body_meta'][bname]
                fastener_instances.append(dict(
                    id=_fastener_trace_id(fspec['prefix'], bname, f_idx),
                    body_name=bname,
                    part_id=p['id'],
                    label=p['label'],
                    spec_label=fspec['spec_label'],
                    standard=fspec['standard'],
                    kind=fspec['kind'],
                    group=p['group'],
                    step=int(fspec['step']),
                    stage=fspec['stage'],
                    layer=p['layer'],
                    target=fspec['target'],
                    axis_local=list(fspec['axis_local']),
                    stroke_mm=float(fspec['stroke_mm']),
                    diameter_mm=float(fspec['diameter_mm']),
                    length_mm=float(fspec['length_mm']),
                    center_local=bmeta['center'],
                    bbox_local=bmeta['bbox'],
                    qty_in_part=p['instance_count'],
                ))

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
        non_countable_parts=list(config.get('non_countable_parts', [])),
        procedural_parts=list(config.get('procedural_parts', [])),
        steps=steps,
        visibility_layers=layers,
        fastener_specs=fastener_specs,
        fastener_instances=fastener_instances,
        bom_groups=config['bom_groups'],
        parts=parts,
        keys=keys_out,
        controller_pads=pads_out,
        spine_grooves=spine_grooves,
        matrix_pins=pins_spec,
        cad_verification=cad_verification,
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
    cfg = config or {}
    dur = float(cfg.get('duration_sec', 36.0))
    steps = cfg.get('steps', [])
    layers = cfg.get('visibility_layers', [])
    step_buttons = ''.join(
        f'<button type="button" class="step-btn" data-step="{idx}" aria-pressed="false" '
        f'title="{s["code"]} · {s["label"]} (Hotkey: {idx})">'
        f'<span class="step-lbl-full">STEP {idx}</span><span class="step-lbl-short">S{idx}</span></button>'
        for idx, s in enumerate(steps, 1)
    )
    layer_buttons = (
        '<button type="button" id="btn-layers-all" class="layer-btn layer-all" data-layer="all" '
        'aria-pressed="true" title="Show all layers">ALL</button>'
        + ''.join(
            f'<button type="button" class="layer-btn" data-layer="{ly["id"]}" aria-pressed="true" '
            f'title="{ly.get("title", ly["label"])} · Shift/DblClick: Solo">{ly["label"]}</button>'
            for ly in layers
        )
    )
    ticks = [
        (0.0, '0s', '01 · DIM'),
        (4.05, '4s', '01 · BUILD'),
        (11.0, '11s', '02 · X-RAY'),
        (16.0, '16s', '03 · CORE'),
        (20.0, '20s', '04 · SEAT'),
        (26.0, '26s', '05 · BOM'),
        (32.0, '32s', '06 · REPORT'),
        (dur, f'{int(dur)}s', 'END'),
    ]
    tick_buttons = ''.join(
        f'<button type="button" class="phase-tick" data-seek="{t:.2f}" style="left:{(t / dur) * 100:.3f}%" '
        f'title="Jump to {lbl} ({t:.1f}s)">{txt}</button>'
        for t, txt, lbl in ticks
    )
    hero_html = (
        f'<img id="motion-fallback-img" src="{fallback_hero}" alt="46es v5 assembly">'
        if fallback_hero else ''
    )
    return f'''<section id="motion-stage" class="motion-stage" aria-label="46es v5 3D Technical Assembly Guide">
  <div class="stage-frame" id="stage-frame">
    <div id="motion-canvas" class="motion-canvas" aria-label="46es v5 3D interactive assembly canvas"></div>
    <svg id="motion-overlay" class="motion-overlay" viewBox="0 0 1920 1080" preserveAspectRatio="none" aria-hidden="true"></svg>
    <div class="stage-header" aria-hidden="true">
      <div class="brand-tag"><span class="brand-code">46ES-V5</span><span class="brand-sep">/</span><span id="hud-phase-code" class="phase-code">01 · DIM + EXPLODE</span></div>
      <div id="hud-telemetry" class="hud-telemetry" hidden></div>
      <div class="header-right">
        <div id="hud-cam-chip" class="hud-cam-chip" hidden>FREE ORBIT</div>
        <div class="time-readout"><span id="hud-time-big">00.0</span><span class="unit">s</span><span class="time-total">/ {dur:.1f}s</span></div>
      </div>
    </div>
    <div id="hud-bolt-tag" class="hud-bolt-tag" hidden aria-hidden="true"></div>
    <div id="hud-pick" class="hud-pick" hidden aria-live="polite"></div>
    <div id="hud-legend" class="hud-legend" hidden aria-label="Scene legend"></div>
    <div id="hud-bom" class="hud-bom" hidden aria-label="BOM inventory grid">
      <div class="bom-head">
        <span class="bom-title">BOM</span>
        <div id="bom-legend" class="bom-legend" aria-label="Assembly step groups"></div>
        <span id="bom-total-badge" class="bom-total">—</span>
      </div>
      <div id="bom-grid" class="bom-grid"></div>
    </div>
    <div id="hud-report-panel" class="hud-report-panel" hidden aria-label="Build verification report">
      <div id="report-legend" class="report-legend" aria-label="Assembly step breakdown"></div>
      <div id="hud-report" class="hud-report">
        <div class="rep-cell"><span class="rep-k">ENVELOPE</span><strong id="rep-env" class="rep-v">—</strong><span id="rep-env-sub" class="rep-sub">—</span></div>
        <div class="rep-cell"><span class="rep-k">3D PRINT</span><strong id="rep-print" class="rep-v">—</strong><span id="rep-print-sub" class="rep-sub">—</span></div>
        <div class="rep-cell"><span class="rep-k">FASTENERS</span><strong id="rep-fast" class="rep-v">—</strong><span id="rep-fast-sub" class="rep-sub">—</span></div>
        <div class="rep-cell"><span class="rep-k">KEYS · LAYOUT</span><strong id="rep-keys" class="rep-v">—</strong><span id="rep-keys-sub" class="rep-sub">—</span></div>
        <div class="rep-cell"><span class="rep-k">MATRIX · WIRE</span><strong id="rep-matrix" class="rep-v">—</strong><span id="rep-matrix-sub" class="rep-sub">—</span></div>
        <div class="rep-cell rep-ok"><span class="rep-k">CAD FIT</span><strong id="rep-fit" class="rep-v">—</strong><span id="rep-fit-sub" class="rep-sub">—</span></div>
      </div>
    </div>
    <div id="motion-loading" class="motion-loading" role="status"><span class="load-code">46ES-V5</span><span id="motion-status-text">LOADING CAD</span></div>
    <div id="motion-fallback" class="motion-fallback" hidden>
      {hero_html}
      <div class="fallback-badge">WEBGL UNAVAILABLE · STATIC CAD FALLBACK</div>
    </div>
  </div>
  <div class="control-bar" role="region" aria-label="Sequence and 3D inspection controls">
    <div class="ctrl-row ctrl-row-1">
      <button id="btn-play" class="ctrl-play" type="button" aria-label="Play or pause" aria-pressed="false" title="Play / Pause (Space)">▶</button>
      <button id="btn-speed" class="ctrl-speed" type="button" aria-label="Playback speed" title="Toggle speed (0.5× / 1× / 1.5×)">1×</button>
      <div class="scrubber-wrap">
        <input id="timeline-scrubber" class="scrubber" type="range" min="0" max="{dur:g}" step="0.05" value="0" aria-label="Timeline scrubber (seconds)">
        <div class="phase-ticks">{tick_buttons}</div>
      </div>
      <span id="ctrl-time" class="ctrl-time">00.0s</span>
      <button id="btn-spec" class="ctrl-spec" type="button" title="Open and scroll to Spec, BOM & SVG Diagrams">SPEC ↓</button>
    </div>
    <div class="ctrl-row ctrl-row-2">
      <div class="mob-drawer-bar">
        <button id="btn-mob-layers" class="mob-drawer-btn" type="button" aria-expanded="false">LAYERS ▾</button>
        <button id="btn-mob-view" class="mob-drawer-btn" type="button" aria-expanded="false">VIEW ▾</button>
      </div>
      <div id="layer-toggles" class="ctrl-group layer-toggles" role="group" aria-label="Layer visibility toggles">{layer_buttons}</div>
      <div id="view-toggles" class="ctrl-group view-toggles" role="group" aria-label="Camera presets and inspection tools">
        <button type="button" class="view-btn" data-preset="iso" aria-pressed="false" title="Isometric View">ISO</button>
        <button type="button" class="view-btn" data-preset="top" aria-pressed="false" title="Top View">TOP</button>
        <button type="button" class="view-btn" data-preset="front" aria-pressed="false" title="Front View">FRT</button>
        <button type="button" class="view-btn" data-preset="side" aria-pressed="false" title="Side View">SID</button>
        <button type="button" class="view-btn" data-preset="bottom" aria-pressed="false" title="Bottom Underside View">BTM</button>
        <span class="ctrl-sep" aria-hidden="true"></span>
        <button type="button" id="btn-turntable" class="tool-btn" aria-pressed="false" title="Auto 360° Turntable">⟳</button>
        <button type="button" id="btn-explode" class="tool-btn" aria-pressed="false" title="Manual Exploded View (Hotkey: E)">EXP</button>
        <button type="button" id="btn-xray" class="tool-btn" aria-pressed="false" title="Manual X-Ray Inspection (Hotkey: X)">XRAY</button>
        <button type="button" id="btn-reset-view" class="tool-btn" title="Reset Camera & Layers (Hotkey: R)">↺</button>
      </div>
      <div id="step-toggles" class="ctrl-group step-toggles" role="group" aria-label="Manual assembly steps">{step_buttons}</div>
    </div>
  </div>
</section>'''
