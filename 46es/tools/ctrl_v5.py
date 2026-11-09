"""Pro Micro bracket for v5 (mount redesign phase 2, 2026-11-09): screwless snap retention.

The board hangs component side down under the left plate (PCB Z 2.0-3.6, USB at -X). It goes in
by rotation: the +X end slides under a shallow end lip, then the -X end is pressed in until two
arms that flex in Y snap under the component side. Corner shoulders beside the USB opening take
the unplug pull (-X), the end wall takes the plug push (+X); together they also stop the board
turning about Z. Ledges and the screw block bear on the solder side (+Z). The bracket is one
body on two M2 screws through the left plate, placed in the unwired zone (pins 1-4) between the
pad rows. The old gate, its M2x5 and nut are gone.

Everything is derived from the PCB frame (TBD_ctrl_*) and checked here against keep-outs:
wired pads (firmware pins, solder and component side), switch housings and pins, the USB plug
envelope, the mounts and the plate's 16.5 switch reliefs. The K1 +x and K23 -x PCB pegs of the
5-pin switches overlap the Pro Micro corners themselves (review CAD: Z 2.7 vs PCB top 3.56), so
they are clipped in assembly and left out of the checks (CLIPPED_PEGS).

Used by tools/build_seam_v5.py (feature emission and checks).
"""
import json
import math
from pathlib import Path

from shapely.affinity import rotate
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from make_key_dxf import load_keys, rect
from mounts_v5 import (MIN_WALL, MOUNT_PIN_CLEARANCE, RELIEF_FLOOR_Z, SWITCH_BODY_Z, hexagon, profiles as mount_profiles,
                       ring, switch_pins, layers as mount_layers)

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / 'firmware/46es_kbfirmware.json'

# --- Pro Micro frame (document values, checked in build_seam_v5.check_ctrl) ------------------------------------
PCB_X, PCB_Y = 114.381, 13.064485      # TBD_ctrl_X, TBD_ctrl_Y (lower-left, USB end at -X)
PCB_L, PCB_W = 33.0, 18.0              # TBD_ctrl_L, TBD_ctrl_W (M15 unmeasured)
PCB_Z, PCB_T = 2.0, 1.6                # TBD_ctrl_pcb_Z (component face), REF_ctrl_pcb_T
PLUG_W = 12.0                          # TBD_usb_plug_W
PLATE_BOTTOM = 8.0                     # TBD_frame_T + TBD_standoff_H
ROOF_GAP, ROOF_T = 0.3, 1.5            # split_bracket_gap, split_bracket_T
M2_SEAT_Z, M2_L = 10.2, 6.0            # split_M2_plate_seat_Z (NBK SSH-M2-6, tip Z 4.2)
M2_CLEAR_D, M2_HEAD_D = 2.4, 4.4       # split_M2_clear_D, split_M2_head_D
NUT_AF, NUT_H = 4.0, 1.6               # DIN 934 M2
NUT_POCKET_AF = 4.4

# Pro Micro pin-out, pin 1 at the USB end. Pads and component-side parts follow the Arduino Pro Micro reference and
# are the one definition of the board: the review model (tools/build_assembly_reference_v5.py) draws it from these
# values and verify_assembly_reference_v5 checks the evaluated bodies against them.
# Pad n centre X = PCB_X + 3.8 + 2.54 (n - 1), rows 1.27 inside the long edges, so pad 12's ring ends 0.39 from the
# +X end. M15 (real board) is still unmeasured.
PINOUT = (('D3', 'D2', 'GND', 'GND', 'D1', 'D0', 'D4', 'C6', 'D7', 'E6', 'B4', 'B5'),
          ('RAW', 'GND', 'RST', 'VCC', 'F4', 'F5', 'F6', 'F7', 'B1', 'B3', 'B2', 'B6'))
PAD_PITCH, PAD_X0, PAD_EDGE, PAD_R = 2.54, 3.8, 1.27, 0.87
# component side, (x, y) from the PCB lower-left, size, depth below the component face; the MCU is a 45-degree square
COMPONENTS = {'USB': ((-0.75, 5.2), (6.15, 7.6), 2.2), 'REGULATOR': ((8.9, 7.8), (2.7, 2.4), 0.85),
              'CAP_A': ((8.4, 4.0), (3.65, 1.8), 1.25), 'CAP_B': ((8.4, 12.2), (3.65, 1.8), 1.25),
              'CRYSTAL': ((29.1, 6.55), (3.2, 4.9), 0.9)}
MCU = ((19.15, 9.0), 6.85, 0.9)
PART_CLR = 0.3
SOLDER_KEEP_R, SOLDER_KEEP_H = PAD_R + 1.0, 2.5     # wire + fillet above the solder side (wires come from +Z)
COMPONENT_KEEP_R, COMPONENT_KEEP_H = PAD_R + 0.3, 0.5   # solder pushed through to the component side

# --- bracket parameters (design candidates; trial set in order 1) -----------------------------------------------
CLR = 0.3                              # TBD_ctrl_clr: board edge/end to walls
CLR_Z = 0.15                           # board face to lips and ledges
WALL = 1.5
LOW_Z = 1.0                            # bottom of arms, rails, shoulders and end wall
TAB_Z = 0.0                            # arm and end wall bottom (= mount bottom plane); the arm's free end is the release tab
UNDER_SWITCH_Z = SWITCH_BODY_Z - 0.05  # 4.9: top of anything under a switch housing
ROOF_TOP = PLATE_BOTTOM - ROOF_GAP     # 7.7
ROOF_Z = ROOF_TOP - ROOF_T             # 6.2
SUPPORT_Z = PCB_Z + PCB_T + CLR_Z      # 3.75: ledges / screw block bear on the solder side
CATCH_Z = PCB_Z - CLR_Z                # 1.85: lips under the component side
RIB_Z = 4.35                           # centre rib stiffens the roof strip; 0.75 above the board (not a support)
SWITCH_CLR = 0.3                       # bracket to switch housing (print tolerance; mounts use 0.15)
PEG_CLR = MOUNT_PIN_CLEARANCE          # 0.4

SHOULDER_X0 = 113.0                    # K1 centre post (r 1.95 + 0.4) ends at X 112.82
ARM_FREE_X = PCB_X + 0.22              # 114.6: arm free ends (lip + release tab)
ARM_ROOT_X = 123.6                     # root blocks X ARM_ROOT_X..BLOCK_X1
BLOCK_X0, BLOCK_X1 = 118.4, 125.0      # screw block over unwired pads 1-4; pin-5 solder keep-out starts at X 126.47
ARM_T_ROOT, ARM_T_TIP = 1.0, 1.0       # MJF wall 1.0; a taper from a thicker root only stiffens it (more strain)
STOP_GAP = 1.0                         # arm tip outer face to rail: release travel and over-travel stop
LIP_L = 2.5
LIP_FLAT = 1.0                         # lip tip height (MJF 1.0) before the 45-degree lead-in ramp
LEDGE_L = 1.5                          # corner ledges X past the board end
STRIP_HALF = 5.55                      # roof strip half width (pad rows' solder keep-outs end at +-5.77)
RIB_HALF = 1.5
END_RISER_Y1 = 23.2                    # K23 housing (+0.3) starts at Y 23.26 over the end
HOOK_E = 0.4                           # lip overlap of the board edge with the board centred
END_D = 0.98                           # end lips / ledge overlap of the board end (between the pad rows; crystal 0.7 from the end)
M2_XY = ((121.7, PCB_Y + PCB_W / 2 - 3.1), (121.7, PCB_Y + PCB_W / 2 + 3.1))   # nut pockets keep 1.1 / 1.12 walls
CONTACT_R = 3.0                        # screw pads touching the plate bottom
CHAMFER = 0.4                          # entry chamfer on the end lip and ledge
FUSE = 0.1                             # profile extrusions reach this far into their host, never flush with its faces
# Order-1 trial variants (same body, other engagement), placed beside the seam coupons.
TRIALS = {'CTRL_SNAP_TRIAL_A': dict(hook_e=0.25, end_d=0.7, stop_gap=STOP_GAP, offset=(-40.0, -105.0)),
          'CTRL_SNAP_TRIAL_C': dict(hook_e=0.55, end_d=1.2, stop_gap=1.1, offset=(0.0, -105.0))}
BODY = 'CTRL_BRACKET_SPLIT_V1'
PLATE = 'PLATE_L_SPLIT_V1'
CLIPPED_PEGS = {(1, +1), (23, -1)}     # (key, side of MX_GUIDES at +-5.08) clipped in assembly


def frame():
    x0, y0 = PCB_X, PCB_Y
    return dict(x0=x0, x1=x0 + PCB_L, y0=y0, y1=y0 + PCB_W, yc=y0 + PCB_W / 2, zc=PCB_Z, zs=PCB_Z + PCB_T)


def wired_pins():
    """Pad numbers (1-12) wired on each row, from the firmware's row/column pins."""
    data = json.loads(FIRMWARE.read_text(encoding='utf-8-sig'))['keyboard']['pins']
    used = set(data['row']) | set(data['col'])
    rows = [{n for n, name in enumerate(row, 1) if name in used} for row in PINOUT]
    if used - set(PINOUT[0]) - set(PINOUT[1]):
        raise ValueError(f'firmware pins not on the Pro Micro pin-out: {used - set(PINOUT[0]) - set(PINOUT[1])}')
    if rows[0] != rows[1]:
        # the bracket is symmetric in Y; an asymmetric set needs the row orientation measured first
        raise ValueError(f'wired pads differ per row {rows}; check which row faces -Y before reusing the bracket')
    return rows[0]


def pads():
    f = frame()
    wired = wired_pins()
    out = []
    for side in (-1, 1):
        for n in range(1, 13):
            out.append(dict(n=n, side=side, wired=n in wired,
                            center=(f['x0'] + PAD_X0 + PAD_PITCH * (n - 1),
                                    f['y0'] + PAD_EDGE if side < 0 else f['y1'] - PAD_EDGE)))
    return out


def arm_strain(length, t_root, t_tip, deflection, steps=400):
    """Peak bending strain of a cantilever whose thickness tapers linearly, tip load, given tip deflection."""
    def h(x):
        return t_root + (t_tip - t_root) * x / length
    dx = length / steps
    compliance = sum(12 * (length - (i + .5) * dx) ** 2 / h((i + .5) * dx) ** 3 * dx for i in range(steps))
    load = deflection / compliance            # P / (E b)
    return max(6 * load * (length - x) / h(x) ** 2 for x in (i * dx for i in range(steps)))


def nut_hexagon(center, across_flats):
    """Hexagon with flats facing +-X (the screw block is 6.6 wide in X)."""
    return rotate(hexagon(center, across_flats), 90, origin=center)


def bracket(hook_e=HOOK_E, end_d=END_D, stop_gap=STOP_GAP, offset=(0.0, 0.0)):
    """Plan prisms and profile extrusions of one bracket. Returns dict(prisms, lips, cuts, report)."""
    f = frame()
    x0, x1, y0, y1, yc = f['x0'], f['x1'], f['y0'], f['y1'], f['yc']
    plug0, plug1 = yc - PLUG_W / 2, yc + PLUG_W / 2
    keys = {k['index']: k for k in switch_pins()}
    housing = unary_union([k['body'] for k in keys.values()]).buffer(SWITCH_CLR, join_style='mitre')
    prisms, lips = [], []

    def prism(name, shape, z0, z1, circles=None):
        shape = shape.buffer(0)
        assert not shape.is_empty and z1 > z0, name
        prisms.append(dict(name=name, shape=shape, z0=z0, z1=z1, circles=circles))

    # -X region roof, centre strip roof (over the wired zone, between the pad rows)
    reach = CLR + ARM_T_TIP + stop_gap + WALL                     # board edge to rail outer face
    roof = box(SHOULDER_X0, y0 - reach, BLOCK_X1, y1 + reach)
    roof = roof.union(box(BLOCK_X1, yc - STRIP_HALF, x1 + CLR + WALL, yc + STRIP_HALF))
    prism('ROOF', roof.difference(housing), ROOF_Z, ROOF_TOP)
    prism('SCREW_BLOCK', box(BLOCK_X0, y0, BLOCK_X1, y1), SUPPORT_Z, ROOF_Z)
    prism('SCREW_PADS', unary_union([Point(c).buffer(CONTACT_R, quad_segs=24) for c in M2_XY]), ROOF_TOP, PLATE_BOTTOM,
          circles=[(c, CONTACT_R) for c in M2_XY])
    prism('ROOF_RIB', box(BLOCK_X1, yc - RIB_HALF, x1 - end_d + 0.5, yc + RIB_HALF).difference(housing), RIB_Z, ROOF_Z)
    for side, name in ((-1, 'F'), (1, 'B')):
        edge = y0 if side < 0 else y1
        inner = edge + side * CLR                                 # arm inner face
        root_out = inner + side * ARM_T_ROOT
        tip_out = inner + side * ARM_T_TIP
        rail_in = tip_out + side * stop_gap
        rail_out = rail_in + side * WALL
        top = ROOF_TOP if side < 0 else UNDER_SWITCH_Z            # K1 housing over the back rail and corner

        def band(a, b):
            return (min(a, b), max(a, b))
        root = band(inner, rail_out)
        prism(f'ROOT_{name}', box(ARM_ROOT_X, root[0], BLOCK_X1, root[1]), LOW_Z, ROOF_TOP)   # first: touches the roof
        rail = band(rail_in, rail_out)
        prism(f'RAIL_{name}', box(SHOULDER_X0, rail[0], BLOCK_X1, rail[1]), LOW_Z, top)
        arm = Polygon([(ARM_FREE_X, inner), (ARM_ROOT_X + 0.05, inner), (ARM_ROOT_X + 0.05, root_out), (ARM_FREE_X, tip_out)])
        prism(f'ARM_{name}', arm, TAB_Z, UNDER_SWITCH_Z)
        corner = band(rail_out, plug0 - CLR) if side < 0 else band(plug1 + CLR, rail_out)
        prism(f'SHOULDER_{name}', box(SHOULDER_X0, corner[0], x0 - CLR, corner[1]), LOW_Z, top)
        ledge = band(edge, plug0 - CLR) if side < 0 else band(plug1 + CLR, edge)
        prism(f'LEDGE_{name}', box(x0 - CLR - 0.05, ledge[0], x0 + LEDGE_L, ledge[1]), SUPPORT_Z, top)
        # lip: YZ profile, catch face at CATCH_Z, short flat at the tip, lead-in ramp down to LOW_Z on the arm face
        tip = edge - side * hook_e
        face = inner + side * FUSE                                 # inside the arm so the join fuses
        lips.append(dict(name=f'LIP_{name}', plane='YZ', at=ARM_FREE_X + FUSE, length=LIP_L - FUSE,
                         profile=[(face, CATCH_Z), (tip, CATCH_Z), (tip, CATCH_Z - LIP_FLAT), (face, TAB_Z + FUSE)],
                         bbox=(ARM_FREE_X, min(face, tip), ARM_FREE_X + LIP_L, max(face, tip), TAB_Z, CATCH_Z)))
    # +X end, between the pad rows only: pad 12 sits 1.26 from the end and its wires leave toward +X past the wall.
    # Wall (plug push), riser to the roof strip, two end lips under the component side either side of the crystal,
    # ledge over the solder side.
    end0 = x1 + CLR
    band0, band1 = yc - STRIP_HALF, yc + STRIP_HALF
    prism('END_RISER', box(end0, band0, end0 + WALL, END_RISER_Y1), UNDER_SWITCH_Z - FUSE, ROOF_TOP)
    prism('END_WALL', box(end0, band0, end0 + WALL, band1), TAB_Z, UNDER_SWITCH_Z)
    lx0 = x1 - end_d
    (cx, cy), (cl, cw), _ = COMPONENTS['CRYSTAL']
    gap0, gap1 = y0 + cy - PART_CLR, y0 + cy + cw + PART_CLR
    for tag, (a, b) in (('A', (band0, gap0)), ('B', (gap1, band1))):
        lips.append(dict(name=f'END_LIP_{tag}', plane='XZ', y0=a, y1=b,
                         profile=[(lx0, CATCH_Z - LIP_FLAT), (end0 + FUSE, CATCH_Z - LIP_FLAT), (end0 + FUSE, CATCH_Z),
                                  (lx0 + CHAMFER, CATCH_Z), (lx0, CATCH_Z - CHAMFER)],
                         bbox=(lx0, a, end0, b, CATCH_Z - LIP_FLAT, CATCH_Z)))
    lips.append(dict(name='END_LEDGE', plane='XZ', y0=yc - STRIP_HALF + FUSE, y1=END_RISER_Y1 - FUSE,
                     profile=[(lx0 + CHAMFER, SUPPORT_Z), (end0 + FUSE, SUPPORT_Z), (end0 + FUSE, ROOF_Z + 0.5),
                              (lx0, ROOF_Z + 0.5), (lx0, SUPPORT_Z + CHAMFER)],
                     bbox=(lx0, yc - STRIP_HALF, end0, END_RISER_Y1, SUPPORT_Z, ROOF_TOP)))
    cuts = dict(nut=[nut_hexagon(c, NUT_POCKET_AF) for c in M2_XY], nut_z=(SUPPORT_Z - 0.1, ROOF_Z),
                screws=list(M2_XY))
    lip_len = ARM_ROOT_X - (ARM_FREE_X + LIP_L / 2)
    insert = CLR + hook_e                     # worst case: board pushed against this arm
    report = dict(hook_e=hook_e, end_d=end_d, lip_arm_mm=round(lip_len, 2), insert_deflection_mm=round(insert, 2),
                  insert_strain_pct=round(100 * arm_strain(lip_len, ARM_T_ROOT, ARM_T_TIP, insert), 2),
                  stop_deflection_tip_mm=stop_gap,
                  stop_strain_pct=round(100 * arm_strain(ARM_ROOT_X - ARM_FREE_X, ARM_T_ROOT, ARM_T_TIP, stop_gap), 2),
                  release_at_lip_mm=round(stop_gap * (lip_len / (ARM_ROOT_X - ARM_FREE_X)) ** 2 *
                                          (3 - lip_len / (ARM_ROOT_X - ARM_FREE_X)) / 2, 2))
    if report['release_at_lip_mm'] < insert:
        raise ValueError(f'the stop gap does not let the lip clear the board: {report}')
    if offset != (0.0, 0.0):
        dx, dy = offset
        from shapely.affinity import translate
        for p in prisms:
            p['shape'] = translate(p['shape'], dx, dy)
            if p['circles']:
                p['circles'] = [((x + dx, y + dy), r) for (x, y), r in p['circles']]
        for lip in lips:
            if lip['plane'] == 'YZ':
                lip['at'] += dx
                lip['profile'] = [(y + dy, z) for y, z in lip['profile']]
            else:
                lip['y0'] += dy
                lip['y1'] += dy
                lip['profile'] = [(x + dx, z) for x, z in lip['profile']]
            b = lip['bbox']
            lip['bbox'] = (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy, b[4], b[5])
        cuts['nut'] = [translate(h, dx, dy) for h in cuts['nut']]
        cuts['screws'] = [(x + dx, y + dy) for x, y in cuts['screws']]
    return dict(prisms=prisms, lips=lips, cuts=cuts, report=report)


def keepouts():
    """[(name, plan polygon, z0, z1)] the production bracket must not enter."""
    f = frame()
    out = []
    for p in pads():
        if p['wired']:
            c = Point(p['center'])
            out.append((f"solder_side_pad_{p['n']}{'FB'[p['side'] > 0]}", c.buffer(SOLDER_KEEP_R, quad_segs=24),
                        f['zs'], f['zs'] + SOLDER_KEEP_H))
            out.append((f"component_side_pad_{p['n']}{'FB'[p['side'] > 0]}", c.buffer(COMPONENT_KEEP_R, quad_segs=24),
                        f['zc'] - COMPONENT_KEEP_H, f['zc']))
    for name, ((x, y), (l, w), depth) in COMPONENTS.items():
        part = box(f['x0'] + x, f['y0'] + y, f['x0'] + x + l, f['y0'] + y + w)
        out.append((f'component_{name}', part.buffer(PART_CLR - 1e-3, join_style='mitre'), f['zc'] - depth - CLR_Z, f['zc']))
    (mx, my), side, depth = MCU
    mcu = Polygon(rect(f['x0'] + mx, f['y0'] + my, side, side, 45))
    out.append(('component_MCU', mcu.buffer(PART_CLR - 1e-3, join_style='mitre'), f['zc'] - depth - CLR_Z, f['zc']))
    pcb = box(f['x0'], f['y0'], f['x1'], f['y1'])
    out.append(('pcb_with_clearance', pcb.buffer(CLR - 1e-3, join_style='mitre'), f['zc'] - CLR_Z + 1e-3, f['zs'] + CLR_Z - 1e-3))
    plug = box(f['x0'] - 25.0, f['yc'] - PLUG_W / 2, f['x0'], f['yc'] + PLUG_W / 2)
    out.append(('usb_plug', plug, f['zc'] - PCB_T - 3.5, f['zc'] - PCB_T + 3.5))
    for k in switch_pins():
        if not k['body'].intersects(box(100, 0, 165, 45)):
            continue
        out.append((f"switch_{k['index']}_housing", k['body'].buffer(SWITCH_CLR - 1e-3, join_style='mitre'),
                    SWITCH_BODY_Z, PLATE_BOTTOM + 5))
        for j, pin in enumerate(k['pins']):
            side = (0, -1, 1)[j] if j < 3 else 0
            if j in (1, 2) and (k['index'], side) in CLIPPED_PEGS:
                continue
            out.append((f"switch_{k['index']}_pin_{j}", pin.buffer(PEG_CLR - 1e-3), RELIEF_FLOOR_Z, SWITCH_BODY_Z))
    keys = load_keys(.693, .667)
    for i, key in enumerate(keys, 1):
        relief = Polygon(rect(key['x'], key['y'], 16.5, 16.5, key['rot']))
        if relief.intersects(box(100, 0, 165, 45)):
            out.append((f'plate_relief_{i}', relief.buffer(0.3 - 1e-3, join_style='mitre'), PLATE_BOTTOM - 0.01, PLATE_BOTTOM + 2))
    for suffix, profile in mount_profiles().items():
        for z0, z1, shape in mount_layers(profile):
            out.append((f'mount_{suffix}_{z0}_{z1}', shape.buffer(CLR - 1e-3, join_style='mitre'), z0, z1))
    return out


def check(design=None):
    """Raise on any bracket prism (or lip bbox) entering a keep-out; returns the report."""
    design = design or bracket()
    solids = [(p['name'], p['shape'], p['z0'], p['z1']) for p in design['prisms']]
    solids += [(lip['name'], box(*lip['bbox'][:2], *lip['bbox'][2:4]), lip['bbox'][4], lip['bbox'][5]) for lip in design['lips']]
    hits = []
    for name, shape, z0, z1 in solids:
        for kname, kshape, k0, k1 in keepouts():
            if min(z1, k1) - max(z0, k0) <= 1e-6:
                continue
            area = shape.intersection(kshape).area
            if area > 1e-4:
                hits.append(f'{name} x {kname}: {area:.3f} mm2 in Z {max(z0, k0):.2f}-{min(z1, k1):.2f}')
    if hits:
        raise ValueError('controller bracket enters keep-outs:\n  ' + '\n  '.join(hits))
    thin = [p['name'] for p in design['prisms'] if p['shape'].buffer(-MIN_WALL / 2 + 0.11).is_empty]
    if thin:
        raise ValueError(f'bracket prisms thinner than {MIN_WALL - 0.22} mm: {thin}')
    return design['report']


def emit(feature, sketch, design=None, body=BODY, plate=PLATE, references=True):
    """Append the bracket (new body), the plate screw holes and the reference M2 screws/nuts.

    The plate cuts come after the order-1 seam coupon copy: the new head recess would sit 0.04 from the coupon
    trim, and the coupon only tests the seam."""
    design = design or bracket()
    xy = dict(type='origin', name='XY')

    def plane(z):
        return dict(type='offset', base=xy, distance=str(round(z, 6)))

    tag = 'CTRL' if body == BODY else body
    first = True
    for p in design['prisms']:
        if p['circles']:
            for j, ((x, y), r) in enumerate(p['circles'], 1):
                feature('cylinder', f'{tag}_{p["name"]}_{j}', axis=[0., 0., 1.], base=[x, y, round(p['z0'], 6)],
                        height=str(round(p['z1'] - p['z0'], 6)), radius=str(r), operation='join', participants=[body])
            continue
        sk = sketch(f'SK_{tag}_{p["name"]}', plane(p['z0']), ring(p['shape']))
        options = dict(body_names=[body]) if first else dict(targets=[body])
        feature('extrude', f'{tag}_{p["name"]}', sketch=sk, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive', distance=str(round(p['z1'] - p['z0'], 6))),
                operation='new_body' if first else 'join', **options)
        first = False
    for lip in design['lips']:
        if lip['plane'] == 'YZ':        # sketch (Y, Z) on X = at, extruded +X
            base = dict(type='custom', plane=dict(origin=[0., 0., 0.], x_dir=[0., 1., 0.], y_dir=[0., 0., 1.]))
            pl, distance, length = dict(type='offset', base=base, distance=str(round(lip['at'], 6))), None, lip['length']
        else:                           # sketch (X, Z) on Y = y1, extruded toward -Y
            base = dict(type='custom', plane=dict(origin=[0., 0., 0.], x_dir=[1., 0., 0.], y_dir=[0., 0., 1.]))
            pl, length = dict(type='offset', base=base, distance=str(round(-lip['y1'], 6))), lip['y1'] - lip['y0']
        sk = sketch(f'SK_{tag}_{lip["name"]}', pl, [lip['profile']])
        feature('extrude', f'{tag}_{lip["name"]}', sketch=sk, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive', distance=str(round(length, 6))),
                operation='join', targets=[body])
    z0, z1 = design['cuts']['nut_z']
    for i, (hexa, (x, y)) in enumerate(zip(design['cuts']['nut'], design['cuts']['screws']), 1):
        sk = sketch(f'SK_{tag}_NUT_{i}', plane(z0), ring(hexa))
        feature('extrude', f'{tag}_NUT_POCKET_{i}', sketch=sk, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive', distance=str(round(z1 - z0, 6))),
                operation='cut', targets=[body])
        feature('cylinder', f'{tag}_M2_CLEAR_{i}', axis=[0., 0., 1.], base=[x, y, SUPPORT_Z - 0.5],
                height=str(PLATE_BOTTOM - SUPPORT_Z + 1.0), radius='(split_M2_clear_D) / 2',
                operation='cut', participants=[body])
        if plate:
            feature('cylinder', f'PLATE_{tag}_M2_CLEAR_{i}', axis=[0., 0., 1.], base=[x, y, PLATE_BOTTOM - 1.0],
                    height='split_M2_plate_seat_Z - TBD_frame_T - TBD_standoff_H + 1.5', radius='(split_M2_clear_D) / 2',
                    operation='cut', participants=[plate])
            feature('cylinder', f'PLATE_{tag}_M2_HEAD_{i}', axis=[0., 0., 1.], base=[x, y, 'split_M2_plate_seat_Z'],
                    height='4', radius='(split_M2_head_D) / 2', operation='cut', participants=[plate])
        if references:
            # body names as before (guide hardware groups); feature names get _V5 beside the suppressed v4 ones
            name = f'REF_M2_PLATE_{i}'
            feature('cylinder', f'{name}_V5', axis=[0., 0., 1.], base=[x, y, f'split_M2_plate_seat_Z-{M2_L}'],
                    height=str(M2_L), radius='(2 mm) / 2', operation='new_body', body_names=[name])
            feature('cylinder', f'{name}_V5_HEAD_JOIN', axis=[0., 0., 1.], base=[x, y, 'split_M2_plate_seat_Z'],
                    height='1.1', radius='(4 mm) / 2', operation='join', participants=[name])
            sk = sketch(f'{name}_V5_NUT_SK', plane(ROOF_Z - NUT_H), ring(nut_hexagon((x, y), NUT_AF)))
            feature('extrude', f'{name}_V5_NUT_HEX', sketch=sk, profiles=dict(type='all'),
                    extent=dict(convention='total_distance', direction='positive', distance=str(NUT_H)),
                    operation='new_body', body_names=[f'{name}_NUT'])
            feature('cylinder', f'{name}_V5_NUT_THREAD_VOID', axis=[0., 0., 1.], base=[x, y, ROOF_Z - NUT_H - 0.1],
                    height=str(NUT_H + 0.2), radius='1', operation='cut', participants=[f'{name}_NUT'])


def expected_volume(design=None):
    """Prism union (by Z slabs) + lip profiles (their FUSE overlap counted twice) - nut pockets and screw holes."""
    design = design or bracket()
    shapes = [(unary_union([Point(c).buffer(r, quad_segs=256) for c, r in p['circles']]) if p['circles'] else p['shape'],
               p['z0'], p['z1']) for p in design['prisms']]
    zs = sorted({z for _, a, b in shapes for z in (a, b)})
    volume = 0.0
    for a, b in zip(zs, zs[1:]):
        mid = (a + b) / 2
        volume += unary_union([s for s, z0, z1 in shapes if z0 < mid < z1]).area * (b - a)
    for lip in design['lips']:
        length = lip['length'] if lip['plane'] == 'YZ' else lip['y1'] - lip['y0']
        volume += Polygon(lip['profile']).area * length
    z0, z1 = design['cuts']['nut_z']
    nut = design['cuts']['nut'][0].area
    hole = math.pi * (M2_CLEAR_D / 2) ** 2
    for _ in design['cuts']['screws']:
        volume -= nut * (z1 - SUPPORT_Z) + hole * (PLATE_BOTTOM - z1)
    return volume


if __name__ == '__main__':
    d = bracket()
    print(json.dumps(check(d), indent=1))
    print('wired pads per row:', sorted(wired_pins()))
    for name, spec in TRIALS.items():
        t = bracket(spec['hook_e'], spec['end_d'], spec['stop_gap'])
        print(name, json.dumps(check(t)))
