"""Read-only: Z, thickness and extrusion of every model-space LINE, ARC, CIRCLE,
LWPOLYLINE and MTEXT in an AC1024 DWG. Reuses the readers in dwg_census.py.

Usage: python -I dwg_thickness.py <file.dwg> <census_out.json>
Result for 46es_r2_keyboard.dwg (2026-11-03): 229 entities, all Z = 0,
thickness = 0, extrusion = +Z (pure 2D drawing).
"""
import collections
import os
import runpy
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
g = runpy.run_path(os.path.join(HERE, "dwg_census.py"), run_name="census")  # uses sys.argv[1:3]
read_section, Bits, ms, umc, omap = g["read_section"], g["Bits"], g["ms"], g["umc"], g["omap"]
objs = read_section("AcDb:AcDbObjects")


def RD(b):
    return struct.unpack("<d", bytes(b.RC() for _ in range(8)))[0]


def DD(b, default):
    """Bit double with default (R2000+)."""
    c = b.BB()
    if c == 0:
        return default
    if c == 3:
        return RD(b)
    raw = bytearray(struct.pack("<d", default))
    if c == 2:
        raw[4] = b.RC()
        raw[5] = b.RC()
    for i in range(4):
        raw[i] = b.RC()
    return struct.unpack("<d", bytes(raw))[0]


def BT(b):
    return 0.0 if b.B() else b.BD()


def BE(b):
    return (0.0, 0.0, 1.0) if b.B() else (b.BD(), b.BD(), b.BD())


NAMES = {0x11: "ARC", 0x12: "CIRCLE", 0x13: "LINE", 0x4D: "LWPOLYLINE", 0x2C: "MTEXT"}
stats = collections.defaultdict(collections.Counter)
odd = []
for h, loc in omap.items():
    size, k = ms(objs, loc)
    hsz, k = umc(objs, k)
    b = Bits(objs, k * 8)
    t = b.BOT()
    if t not in NAMES:
        continue
    own = b.H()[1]
    while True:  # EED
        n = b.BS()
        if n == 0:
            break
        b.H()
        b.p += 8 * n
    if b.B():  # graphic image
        b.p += 8 * b.BLL()
    mode = b.BB()
    if mode != 2:  # model space only
        continue
    b.BL(); b.B()  # reactors, xdic missing
    cflag = b.BS() >> 8
    if cflag & 0x80: b.BL()
    if cflag & 0x20: b.BL()
    b.BD(); b.BB(); b.BB(); b.BB(); b.RC(); b.B(); b.B(); b.B(); b.BS(); b.RC()
    z, th, ex = 0.0, 0.0, (0.0, 0.0, 1.0)
    if t in (0x11, 0x12):
        b.BD(); b.BD(); z = b.BD(); b.BD()  # centre x, y, z, radius
        th, ex = BT(b), BE(b)
    elif t == 0x13:
        z_zero = b.B()
        x0 = RD(b); DD(b, x0); y0 = RD(b); DD(b, y0)
        if not z_zero:
            z0 = RD(b); z1 = DD(b, z0); z = max(abs(z0), abs(z1))
        th, ex = BT(b), BE(b)
    elif t == 0x4D:
        flag = b.BS()
        if flag & 4: b.BD()          # constant width
        if flag & 8: z = b.BD()      # elevation
        if flag & 2: th = b.BD()     # thickness
        if flag & 1: ex = (b.BD(), b.BD(), b.BD())
    elif t == 0x2C:
        b.BD(); b.BD(); z = b.BD()   # insertion point
        ex = (b.BD(), b.BD(), b.BD())
    s = stats[NAMES[t]]
    s["n"] += 1
    s["z!=0"] += abs(z) > 1e-9
    s["thickness!=0"] += abs(th) > 1e-9
    s["extrusion!=+Z"] += any(abs(a - c) > 1e-9 for a, c in zip(ex, (0, 0, 1)))
    if abs(z) > 1e-9 or abs(th) > 1e-9:
        odd.append((NAMES[t], hex(own), z, th, ex))

for name, s in sorted(stats.items()):
    print(name, dict(s))
print("total model-space entities checked:", sum(s["n"] for s in stats.values()))
print("entities with Z or thickness:", odd[:20])
