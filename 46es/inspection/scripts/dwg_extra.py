"""Read-only extras: AppInfo strings, GROUP object members, dates. Reuses dwg_census helpers."""
import sys, re, json, datetime, runpy
sys.stdout.reconfigure(encoding="utf-8")
PATH = sys.argv[1]
sys.argv = [sys.argv[0], PATH, sys.argv[2]]
g = runpy.run_path(sys.argv[0].replace("dwg_extra.py", "dwg_census.py"), run_name="census")
read_section, Bits, ms, umc, abs_handle, omap = g["read_section"], g["Bits"], g["ms"], g["umc"], g["abs_handle"], g["omap"]
ai = read_section("AcDb:AppInfo")
strs = [s.decode("utf-16-le") for s in re.findall(rb"(?:[\x20-\x7e]\x00){3,}", ai)]
print("AppInfo strings:", strs)
objs = read_section("AcDb:AcDbObjects")
ms_handles = set()
for h, loc in omap.items():
    size, k = ms(objs, loc); hsz, k = umc(objs, k)
    b = Bits(objs, k * 8); t = b.BOT()
    if t != 0x48:
        continue
    own = b.H()[1]
    while True:
        n = b.BS()
        if n == 0: break
        b.H(); b.p += 8 * n
    nre = b.BL(); xmiss = b.B()
    bitsize = size * 8 - hsz
    sb = Bits(objs, k * 8 + bitsize - 1); desc = None
    if sb.B():
        sp = k * 8 + bitsize - 1 - 16; sb.p = sp; dsz = sb.RS()
        sb.p = sp - dsz; desc = sb.TU()
    unnamed = b.BS(); selectable = b.BS(); nh = b.BL()
    hb = Bits(objs, k * 8 + bitsize)
    hb.H()  # parent
    for _ in range(nre): hb.H()
    if not xmiss: hb.H()
    members = [abs_handle(hb.H(), own) for _ in range(nh)]
    print(f"GROUP @{own:#x}: description={desc!r} unnamed={unnamed} selectable={selectable} members={nh}")
    print("   member handles:", [f"{m:X}" for m in members])
def jd(x): return (datetime.datetime(2000, 1, 1, 12) + datetime.timedelta(days=x - 2451545.0)).strftime("%Y-%m-%d %H:%M")
print("TDCREATE", jd(2459384.5307060187), "TDUPDATE", jd(2460078.6232125), "(local time as stored)")
