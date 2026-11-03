"""Independent, read-only census of an AC1024 (R2010) DWG.

Written from the ODA "Open Design Specification for .dwg files" (R2004+ file
structure, section pages, LZ77 variant, object map, R2010 object headers).
It does NOT interpret geometry; it only counts objects by type, reads each
entity's space (entmode) and layer handle, and reads LAYER names, so the
counts can be compared with CADCraft's import. Opens the file read-only.
"""
import struct, sys, json, collections

sys.stdout.reconfigure(encoding="utf-8")
PATH, OUT = sys.argv[1], sys.argv[2]
raw = open(PATH, "rb").read()
report = {"warnings": []}

# ---------------------------------------------------------------- file header
ver = raw[0:6].decode()
maint = raw[0x0B]
codepage = struct.unpack_from("<H", raw, 0x13)[0]
report.update(version=ver, maint_byte=maint, codepage=codepage, file_size=len(raw))

def xor_seq(n):
    s, out = 1, bytearray()
    for _ in range(n):
        s = (s * 0x343FD + 0x269EC3) & 0xFFFFFFFF
        out.append((s >> 16) & 0xFF)
    return bytes(out)

hdr = bytes(a ^ b for a, b in zip(raw[0x80:0x80 + 0x6C], xor_seq(0x6C)))
assert hdr[:11] == b"AcFssFcAJMB", hdr[:12]
(sec_page_amount,) = struct.unpack_from("<I", hdr, 0x40)
(page_map_id,) = struct.unpack_from("<I", hdr, 0x50)
(page_map_addr,) = struct.unpack_from("<Q", hdr, 0x54)
(section_map_id,) = struct.unpack_from("<I", hdr, 0x5C)
report.update(file_id=hdr[:11].decode(), section_page_amount=sec_page_amount)

# ---------------------------------------------------------------- LZ77 (2004)
def decompress(src, out_size):
    dst = bytearray()
    i = 0

    def rb():
        nonlocal i
        b = src[i]; i += 1
        return b

    def lit_len():
        b = rb()
        if 0x01 <= b <= 0x0F:
            return b + 3, 0
        if b == 0:
            t = 0x0F
            b = rb()
            while b == 0:
                t += 0xFF; b = rb()
            return t + b + 3, 0
        return 0, b  # it was an opcode

    def long_off():
        b = rb(); t = 0
        if b == 0:
            t = 0xFF
            b = rb()
            while b == 0:
                t += 0xFF; b = rb()
        return t + b

    def two_byte():
        b1 = rb(); b2 = rb()
        return (b1 >> 2) | (b2 << 6), b1 & 3

    n, op = lit_len()
    dst += src[i:i + n]; i += n
    while i < len(src):
        if op == 0:
            op = rb()
        if op == 0x11:
            break
        if op >= 0x40:
            cb = ((op & 0xF0) >> 4) - 1
            op2 = rb()
            co = (op2 << 2) | ((op & 0x0C) >> 2)
            ll = op & 3
            if ll:
                op = 0
            else:
                ll, op = lit_len()
        elif 0x21 <= op <= 0x3F:
            cb = op - 0x1E
            co, ll = two_byte()
            if ll: op = 0
            else: ll, op = lit_len()
        elif op == 0x20:
            cb = long_off() + 0x21
            co, ll = two_byte()
            if ll: op = 0
            else: ll, op = lit_len()
        elif 0x12 <= op <= 0x1F:
            cb = (op & 0x0F) + 2
            co, ll = two_byte(); co += 0x3FFF
            if ll: op = 0
            else: ll, op = lit_len()
        elif op == 0x10:
            cb = long_off() + 9
            co, ll = two_byte(); co += 0x3FFF
            if ll: op = 0
            else: ll, op = lit_len()
        else:
            raise ValueError(f"bad opcode {op:#x} at {i}")
        start = len(dst) - co - 1
        for k in range(cb):
            dst.append(dst[start + k])
        dst += src[i:i + ll]; i += ll
    if len(dst) < out_size:
        report["warnings"].append(f"decompressed {len(dst)} != expected {out_size}")
    return bytes(dst)

def system_page(addr, expect_type):
    t, dsz, csz, ctype, _ = struct.unpack_from("<5I", raw, addr)
    assert t == expect_type, hex(t)
    data = raw[addr + 20: addr + 20 + csz]
    return decompress(data, dsz) if ctype == 2 else data

# ---------------------------------------------------------------- page map
pm = system_page(page_map_addr + 0x100, 0x41630E3B)
pages = {}
addr = 0x100
j = 0
gaps = 0
while j + 8 <= len(pm):
    num, size = struct.unpack_from("<iI", pm, j); j += 8
    if num < 0:
        j += 16; gaps += 1
    else:
        pages[num] = (addr, size)
    addr += size
report["pages"] = len(pages); report["gap_pages"] = gaps

# ---------------------------------------------------------------- section map
sm = system_page(pages[section_map_id][0], 0x4163003B)
ndesc, _, _, _, _ = struct.unpack_from("<5I", sm, 0)
j = 20
sections = {}
for _ in range(ndesc):
    size, npages, maxdec, _u, comp, sid, enc = struct.unpack_from("<QIIIIII", sm, j); j += 32
    name = sm[j:j + 64].split(b"\0")[0].decode("ascii", "replace"); j += 64
    plist = []
    for _ in range(npages):
        pnum, dsize, start = struct.unpack_from("<IIQ", sm, j); j += 16
        plist.append((pnum, dsize, start))
    sections[name] = dict(size=size, pages=plist, maxdec=maxdec, compressed=comp, id=sid, encrypted=enc)
report["sections"] = {k: dict(size=v["size"], pages=len(v["pages"]), compressed=v["compressed"], encrypted=v["encrypted"]) for k, v in sections.items()}

def read_section(name):
    s = sections[name]
    buf = bytearray(s["size"] + s["maxdec"])
    for pnum, dsize, start in s["pages"]:
        a = pages[pnum][0]
        mask = 0x4164536B ^ a
        h = struct.unpack_from("<8I", raw, a)
        h = [w ^ mask for w in h]
        ptype, secnum, csize, _disk, sstart = h[:5]
        psize = min(s["maxdec"], s["size"] - sstart)
        assert ptype == 0x4163043B, hex(ptype)
        data = raw[a + 32: a + 32 + csize]
        dec = decompress(data, psize) if s["compressed"] == 2 else data
        dec = dec[:psize] if len(dec) >= psize else dec
        buf[start:start + len(dec)] = dec
    return bytes(buf[:s["size"]])

# ---------------------------------------------------------------- bit reader
class Bits:
    def __init__(self, data, bitpos=0):
        self.d = data; self.p = bitpos
    def B(self):
        v = (self.d[self.p >> 3] >> (7 - (self.p & 7))) & 1; self.p += 1; return v
    def bits(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | self.B()
        return v
    def RC(self): return self.bits(8)
    def RS(self): lo = self.RC(); hi = self.RC(); return lo | (hi << 8)
    def RL(self): lo = self.RS(); hi = self.RS(); return lo | (hi << 16)
    def BB(self): return self.bits(2)
    def BS(self):
        c = self.BB()
        return [self.RS, self.RC, lambda: 0, lambda: 256][c]()
    def BL(self):
        c = self.BB()
        return [self.RL, self.RC, lambda: 0, lambda: None][c]()
    def BLL(self):
        n = self.bits(3); v = 0
        for k in range(n):
            v |= self.RC() << (8 * k)
        return v
    def BD(self):
        c = self.BB()
        if c == 0:
            return struct.unpack("<d", bytes(self.RC() for _ in range(8)))[0]
        return [None, 1.0, 0.0, None][c]
    def H(self):
        code = self.bits(4); n = self.bits(4); v = 0
        for _ in range(n):
            v = (v << 8) | self.RC()
        return code, v
    def BOT(self):
        c = self.BB()
        if c == 0: return self.RC()
        if c == 1: return self.RC() + 0x1F0
        return self.RS()
    def TU(self):
        n = self.BS()
        return "".join(chr(self.RS()) for _ in range(n))

def abs_handle(ref, own):
    code, v = ref
    if code in (2, 3, 4, 5): return v
    if code == 6: return own + 1
    if code == 8: return own - 1
    if code == 0xA: return own + v
    if code == 0xC: return own - v
    return v

def umc(b, i):
    v = sh = 0
    while True:
        c = b[i]; i += 1
        v |= (c & 0x7F) << sh; sh += 7
        if not c & 0x80: return v, i

def mc(b, i):
    v = sh = 0
    while True:
        c = b[i]; i += 1
        if c & 0x80:
            v |= (c & 0x7F) << sh; sh += 7
        else:
            v |= (c & 0x3F) << sh
            return (-v if c & 0x40 else v), i

def ms(b, i):
    v = sh = 0
    while True:
        w = b[i] | (b[i + 1] << 8); i += 2
        v |= (w & 0x7FFF) << sh; sh += 15
        if not w & 0x8000: return v, i

# ---------------------------------------------------------------- object map
hs = read_section("AcDb:Handles")
omap = {}
i = 0
while i < len(hs):
    size = (hs[i] << 8) | hs[i + 1]; i += 2
    if size == 2:
        break
    end = i + size - 2
    lh = ll = 0
    while i < end:
        dh, i = umc(hs, i); dl, i = mc(hs, i)
        lh += dh; ll += dl
        omap[lh] = ll
    i = end + 2
report["objects_in_map"] = len(omap)

# ---------------------------------------------------------------- classes (names, best effort)
classes = {}
try:
    cs = read_section("AcDb:Classes")
    b = Bits(cs, 16 * 8)
    size = b.RL()
    hsize = b.RL()          # R2010, maint > 3
    bitsize = b.RL()
    maxnum = b.BS(); b.RC(); b.RC(); b.B()
    # string stream (R2007+): end flag at bitsize + 191
    sp = bitsize + 191
    sb = Bits(cs, sp)
    if sb.B():
        sp -= 16; sb.p = sp; dsz = sb.RS()
        if dsz & 0x8000:
            sp -= 16; sb.p = sp; hi = sb.RS(); dsz = (dsz & 0x7FFF) | (hi << 15)
        sb.p = sp - dsz
    while b.p < bitsize + 24 * 8 - 64 and len(classes) <= maxnum - 500:
        num = b.BS(); pflags = b.BS()
        app = sb.TU(); cpp = sb.TU(); dxf = sb.TU()
        zombie = b.B(); item = b.BS(); ninst = b.BL(); dv = b.BS(); mv = b.BS(); b.BL(); b.BL()
        classes[num] = dict(dxf=dxf, cpp=cpp, app=app, item_class_id=item, entity=(item == 0x1F2), instances=ninst)
        if num >= maxnum:
            break
except Exception as ex:  # noqa
    report["warnings"].append(f"class parse failed: {ex!r}")
report["classes"] = classes

# ---------------------------------------------------------------- objects
FIXED = {0x01: "TEXT", 0x02: "ATTRIB", 0x03: "ATTDEF", 0x04: "BLOCK", 0x05: "ENDBLK", 0x06: "SEQEND", 0x07: "INSERT",
         0x08: "MINSERT", 0x0A: "VERTEX_2D", 0x0B: "VERTEX_3D", 0x0C: "VERTEX_MESH", 0x0D: "VERTEX_PFACE", 0x0E: "VERTEX_PFACE_FACE",
         0x0F: "POLYLINE_2D", 0x10: "POLYLINE_3D", 0x11: "ARC", 0x12: "CIRCLE", 0x13: "LINE", 0x14: "DIMENSION_ORDINATE",
         0x15: "DIMENSION_LINEAR", 0x16: "DIMENSION_ALIGNED", 0x17: "DIMENSION_ANG3PT", 0x18: "DIMENSION_ANG2LN",
         0x19: "DIMENSION_RADIUS", 0x1A: "DIMENSION_DIAMETER", 0x1B: "POINT", 0x1C: "3DFACE", 0x1D: "POLYLINE_PFACE",
         0x1E: "POLYLINE_MESH", 0x1F: "SOLID", 0x20: "TRACE", 0x21: "SHAPE", 0x22: "VIEWPORT", 0x23: "ELLIPSE", 0x24: "SPLINE",
         0x25: "REGION", 0x26: "3DSOLID", 0x27: "BODY", 0x28: "RAY", 0x29: "XLINE", 0x2A: "DICTIONARY", 0x2B: "OLEFRAME",
         0x2C: "MTEXT", 0x2D: "LEADER", 0x2E: "TOLERANCE", 0x2F: "MLINE", 0x30: "BLOCK_CONTROL", 0x31: "BLOCK_HEADER",
         0x32: "LAYER_CONTROL", 0x33: "LAYER", 0x34: "STYLE_CONTROL", 0x35: "STYLE", 0x38: "LTYPE_CONTROL", 0x39: "LTYPE",
         0x3C: "VIEW_CONTROL", 0x3D: "VIEW", 0x3E: "UCS_CONTROL", 0x3F: "UCS", 0x40: "VPORT_CONTROL", 0x41: "VPORT",
         0x42: "APPID_CONTROL", 0x43: "APPID", 0x44: "DIMSTYLE_CONTROL", 0x45: "DIMSTYLE", 0x46: "VX_CONTROL",
         0x47: "VX_TABLE_RECORD", 0x48: "GROUP", 0x49: "MLINESTYLE", 0x4A: "OLE2FRAME", 0x4C: "LONG_TRANSACTION",
         0x4D: "LWPOLYLINE", 0x4E: "HATCH", 0x4F: "XRECORD", 0x50: "PLACEHOLDER", 0x51: "VBA_PROJECT", 0x52: "LAYOUT",
         0x1F2: "PROXY_ENTITY", 0x1F3: "PROXY_OBJECT"}
ENTITY_FIXED = set(range(0x01, 0x2A)) - {0x2A} | {0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x4A, 0x4D, 0x4E, 0x1F2}
ENTITY_FIXED -= {0x09}

objs = read_section("AcDb:AcDbObjects")
census = collections.Counter()
ent_space = collections.Counter()
ent_layer = collections.Counter()
layers = {}
blocknames = {}
mtexts = {}
ms_arcs = []
extra_pts = []
proxy_cls = []
ent_owner_h = {}
ent_owner = collections.Counter()
errors = 0
for h, loc in sorted(omap.items()):
    try:
        size, k = ms(objs, loc)
        hsz, k = umc(objs, k)
        b = Bits(objs, k * 8)
        t = b.BOT()
        name = FIXED.get(t) or (classes.get(t, {}).get("dxf") or f"CLASS_{t}")
        is_ent = t in ENTITY_FIXED or classes.get(t, {}).get("entity", False)
        census[name] += 1
        own_code, own = b.H()
        # EED
        while True:
            n = b.BS()
            if n == 0:
                break
            b.H(); b.p += 8 * n
        if is_ent:
            if b.B():
                gsz = b.BLL(); b.p += 8 * gsz
            mode = b.BB()
            nreac = b.BL(); xdic_missing = b.B()
            # ENC colour
            cval = b.BS(); cflag = cval >> 8
            if cflag & 0x80: b.BL()
            if cflag & 0x20: b.BL()
            b.BD()                     # linetype scale
            ltf = b.BB(); psf = b.BB(); matf = b.BB(); b.RC()
            b.B(); b.B(); b.B()        # visual style flags
            b.BS(); b.RC()             # invisibility, lineweight
            if t in (0x11, 0x12) and mode == 2:   # ARC / CIRCLE in model space
                cx, cy, cz, r = b.BD(), b.BD(), b.BD(), b.BD()
                if not b.B(): b.BD()          # BT thickness
                if not b.B(): b.BD(); b.BD(); b.BD()  # BE extrusion
                a0 = a1 = None
                if t == 0x11: a0, a1 = b.BD(), b.BD()
                ms_arcs.append(dict(h=f"{own:X}", type="ARC" if t == 0x11 else "CIRCLE", cx=cx, cy=cy, r=r, a0=a0, a1=a1))
            if t == 0x1B:   # POINT: BD x, BD y, BD z
                extra_pts.append((own, b.BD(), b.BD(), b.BD()))
            hb = Bits(objs, k * 8 + size * 8 - hsz)
            owner = abs_handle(hb.H(), own) if mode == 0 else None
            for _ in range(nreac): hb.H()
            if not xdic_missing: hb.H()
            if cflag & 0x40: hb.H()
            lay = abs_handle(hb.H(), own)
            space = {0: "owned(block)", 1: "paper", 2: "model"}.get(mode, f"mode{mode}")
            ent_space[(space, name)] += 1
            ent_layer[(space, lay)] += 1
            if owner is not None:
                ent_owner[(owner, name)] += 1
                ent_owner_h[own] = owner
        if t == 0x1F3:
            nre = b.BL(); b.B()
            for _ in range(nre): pass
            proxy_cls.append(b.BL())
        if t in (0x33, 0x31, 0x2C):
            bitsize = size * 8 - hsz
            sb = Bits(objs, k * 8 + bitsize - 1)
            if sb.B():
                sp = k * 8 + bitsize - 1 - 16; sb.p = sp; dsz = sb.RS()
                if dsz & 0x8000:
                    sp -= 16; sb.p = sp; hi = sb.RS(); dsz = (dsz & 0x7FFF) | (hi << 15)
                sb.p = sp - dsz
                txt = sb.TU()
                if t == 0x33: layers[own] = txt
                elif t == 0x31: blocknames[own] = txt
                else: mtexts[own] = txt
    except Exception as ex:  # noqa
        errors += 1
        if errors < 10:
            report["warnings"].append(f"object {h:#x}: {ex!r}")

report["object_parse_errors"] = errors
report["census"] = dict(census.most_common())
report["entities_by_space"] = {f"{s}|{n}": c for (s, n), c in sorted(ent_space.items())}
report["layer_names_by_handle"] = {f"{k:#x}": v for k, v in layers.items()}
report["entity_layer_use"] = {f"{s}|{layers.get(l, hex(l))}": c for (s, l), c in sorted(ent_layer.items(), key=lambda x: (x[0][0], x[0][1]))}
per_block = collections.defaultdict(dict)
for (o, n), c in ent_owner.items():
    per_block[f"{blocknames.get(o, '?')}@{o:#x}"][n] = c
report["block_names"] = {f"{k:#x}": v for k, v in blocknames.items()}
report["entities_per_block"] = dict(per_block)
dblocks = {k for k, v in blocknames.items() if v.startswith("*D")}
report["orphan_dim_blocks"] = {
    f"{k:#x}": dict(mtext=[mtexts[h] for h, o in ent_owner_h.items() if o == k and h in mtexts],
                    points=[(round(x, 4), round(y, 4), round(z, 4)) for (h, x, y, z) in extra_pts if ent_owner_h.get(h) == k])
    for k in sorted(dblocks)}
report["model_space_arcs_circles"] = ms_arcs
report["proxy_object_classes"] = [classes.get(c, {}).get("dxf", c) for c in proxy_cls]
report["model_space_mtext"] = {f"{h:#x}": v for h, v in mtexts.items() if h not in ent_owner_h}
json.dump(report, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)

print(json.dumps({k: report[k] for k in ("version", "maint_byte", "codepage", "file_id", "pages", "gap_pages", "objects_in_map", "object_parse_errors")}, ensure_ascii=False))
print("sections:", json.dumps(report["sections"], ensure_ascii=False))
print("classes:", {k: (v["dxf"], "ENT" if v["entity"] else "obj", v["instances"]) for k, v in classes.items()})
print("census:", report["census"])
print("entities by space:", json.dumps(report["entities_by_space"], ensure_ascii=False, indent=0))
print("layers:", report["layer_names_by_handle"])
print("entity layer use:", report["entity_layer_use"])
print("block records:", len(blocknames))
for n, d in sorted(per_block.items()):
    print(f"   {n}: {d}")
print("blocks with no entities:", sorted(f"{v}@{k:#x}" for k, v in blocknames.items() if f"{v}@{k:#x}" not in per_block))
print("orphan *D blocks:", json.dumps(report["orphan_dim_blocks"], ensure_ascii=False, indent=1))
print("proxy object classes:", report["proxy_object_classes"])
print("model-space MTEXT:", report["model_space_mtext"])
print("warnings:", report["warnings"])
