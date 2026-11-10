#!/usr/bin/env python3
"""Build the 46es design-review and assembly-guide page from a JSON spec.

The page follows the CAD model without hand work:
  solidcraft-cli eval      -> bodies (volume, bbox), parameters, timeline errors
  solidcraft-cli snapshot  -> one PNG per render in the spec (visible bodies, camera, section)
  model/measurements.csv   -> measurement status grid and header chip
  diagrams.py              -> wiring, pin, snap, magnet, test and keycap diagrams (SVG) from the generator sources
The text (assembly steps, review notes) lives in the spec. Numbers in the text can be
tokens that are filled from the model: {{p:PARAM}} parameter value, {{v:BODY}} volume in cm3,
{{d:BODY}} bbox size, {{n:PATTERN}} number of bodies matching a pattern or @group.

Usage (paths may be relative to this folder):
  python build_guide.py                                  # guide_v5.json -> out/
  python build_guide.py --out D:/work/zzskm.github.io/keyboard-46es --clean-img
  python build_guide.py --only hero,sec-so1              # re-render just these
Options: --spec FILE  --cli PATH  --jobs N  --skip-renders  --only IDS  --clean-img
Renders are cached in .cache/renders by the shape digest, appearance and list position of each body they
show + render settings (plan 3-4), so a text-only change or a rebuild that reproduces the bodies takes
seconds, and a model change re-renders only the views showing a changed body. The eval result is shared
by model hash (tools/cad_eval_cache.py).
"""
import argparse
import concurrent.futures as cf
import csv
import datetime
import fnmatch
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
import assembly
import diagrams

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE.parent / "inspection/scripts"))
from common import CLI as DEFAULT_CLI  # noqa: E402  (SOLIDCRAFT_CLI or the default install path)
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600'
         '&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">')


def die(msg):
    raise SystemExit(f"build_guide: {msg}")


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, timeout=900):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    if r.returncode:
        die(f"command failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r


# ---------------------------------------------------------------- model data
def model_eval(cli, model, model_sha):
    """The shared evaluation cache (tools/cad_eval_cache.py, 46es/.cache/eval), keyed by the model bytes."""
    from cad_eval_cache import evaluation
    data, path = evaluation(model, cli)
    if not path.name.startswith(model_sha[:16]):
        die(f"{model} changed while the guide was built")
    return data


def expand(items, names, groups, where):
    out = []
    for it in items:
        if it.startswith("@"):
            if it[1:] not in groups:
                die(f"{where}: unknown group {it}")
            out += expand(groups[it[1:]], names, groups, where)
            continue
        hits = [n for n in names if fnmatch.fnmatchcase(n, it)]
        if not hits:
            die(f"{where}: pattern {it!r} matches no body in the model")
        out += hits
    seen, res = set(), []
    for n in out:
        if n not in seen:
            seen.add(n)
            res.append(n)
    return res


# ---------------------------------------------------------------- renders
def body_looks(model):
    """Per live body: its shape digest, its appearance entry and its position in the body list."""
    from cad_model import document, shape_digests
    appearances = document(model).get("appearances", {}).get("bodies", {})
    return {name: [digest, appearances.get(name), index]
            for index, (name, digest) in enumerate(shape_digests(model).items())}


def render_job(cli, model, looks, r, names, groups, cameras, defaults, cached_only=False):
    rid = r["id"]
    show = expand(r["show"], names, groups, rid)
    if r.get("hide"):
        hide = set(expand(r["hide"], names, groups, rid))
        show = [n for n in show if n not in hide]
    cam = r.get("camera", defaults["camera"])
    if isinstance(cam, str):
        if cam not in cameras:
            die(f"{rid}: unknown camera {cam}")
        cam = cameras[cam]
    w, h = r.get("size", defaults["size"])
    styles = []
    for s in r.get("style", []):
        opts = [f"{k}={s[k]}" for k in ("opacity", "color") if k in s]
        styles += [f"{n}:{','.join(opts)}" for n in expand([s["body"]], names, groups, rid)]
    script = [{"command": "browser.visibility", "params": {"visible": False, "folder": "all"}},
              {"command": "browser.visibility", "params": {"visible": True, "items": show}}]
    # Keyed by what the render shows (plan 3-4), not by the model file: a rebuild or a change to hidden bodies
    # keeps it. looks[n] = shape digest, appearance and list position (default colours follow the position).
    drawn = list(dict.fromkeys(show + [n for s in r.get("style", []) for n in expand([s["body"]], names, groups, rid)]))
    key_src = json.dumps({"bodies": {n: looks[n] for n in drawn}, "script": script, "camera": cam, "size": [w, h],
                          "section": r.get("section"), "styles": styles, "v": 2}, sort_keys=True)
    key = hashlib.sha256(key_src.encode()).hexdigest()[:20]
    rdir = CACHE / "renders"
    png = rdir / f"{rid}-{key}.png"
    if png.exists():
        return rid, png, False
    if cached_only:
        die(f"render {rid} is not cached for the current model/settings; run without --skip-renders/--only")
    rdir.mkdir(parents=True, exist_ok=True)
    sp = rdir / f"{rid}-{key}.script.json"
    tmp = rdir / f"{rid}-{key}.tmp.png"
    sp.write_text(json.dumps(script), encoding="utf-8")
    cmd = [cli, "snapshot", sp, "--in", model, "--out", tmp, "--width", w, "--height", h,
           "--camera", json.dumps(cam), "--no-grid", "--no-axes"]
    if r.get("section"):
        cmd += ["--section", r["section"]]
    for s in styles:
        cmd += ["--body", s]
    run(cmd)
    tmp.replace(png)
    sp.unlink(missing_ok=True)
    return rid, png, True


# ---------------------------------------------------------------- text
TOKEN = re.compile(r"\{\{([pvdn]):([^}]+)\}\}")


def fmt_num(v):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.3f}".rstrip("0").rstrip(".")


class Ctx:
    def __init__(self, spec, ev, names, groups):
        self.spec, self.ev, self.names, self.groups = spec, ev, names, groups
        self.bodies = {b["name"]: b for b in ev["bodies"]}
        self.params = {p["name"]: p["value"] for p in ev["params"] if p.get("value") is not None}
        self.sizes = {}

    def dims(self, name):
        bb = self.bodies[name]["bbox"]
        return [bb["max"][i] - bb["min"][i] for i in range(3)]

    def text(self, s):
        if s is None:
            return ""
        if isinstance(s, list):
            return "".join(f"<p>{self.text(x)}</p>" for x in s)

        def rep(m):
            kind, arg = m.group(1), m.group(2).strip()
            if kind == "p":
                if arg not in self.params:
                    die(f"text token: unknown parameter {arg}")
                return fmt_num(self.params[arg])
            if kind in "vd" and arg not in self.bodies:
                die(f"text token: unknown body {arg}")
            if kind == "v":
                return f"{self.bodies[arg]['volume_mm3'] / 1000:.1f}"
            if kind == "d":
                return " × ".join(f"{x:.1f}" for x in self.dims(arg))
            return str(len(expand([arg], self.names, self.groups, "text")))
        return TOKEN.sub(rep, s)


def tag_strip(s):
    return re.sub(r"<[^>]+>", "", s)


def pill(tone, text):
    return f'<span class="pill {html.escape(tone)}">{text}</span>'


def figure(ctx, rid, caption=None, alt=None, eager=False):
    w, h = ctx.sizes[rid]
    cap = ctx.text(caption) if caption else ""
    alt = alt or tag_strip(cap) or rid
    lazy = "" if eager else ' loading="lazy"'
    out = (f'<figure><a href="img/{rid}.png"><img src="img/{rid}.png" width="{w}" height="{h}"{lazy} '
           f'alt="{html.escape(alt)}"></a>')
    if cap:
        out += f"<figcaption>{cap}</figcaption>"
    return out + "</figure>"


def figs(ctx, items, cols=2):
    if not items:
        return ""
    cls = {1: "figs one", 3: "figs three"}.get(cols, "figs")
    return f'<div class="{cls}">' + "".join(figure(ctx, f["render"], f.get("caption"), f.get("alt")) for f in items) + "</div>"


# ---------------------------------------------------------------- measurements
def measurements(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    head = rows[0]
    col = {k: head.index(k) for k in ("id", "항목", "상태", "실측값")}
    return [{k: r[i] for k, i in col.items()} for r in rows[1:] if r and r[0].startswith("M")]


def measurement_chip(rows):
    done = sum(1 for r in rows if r["상태"].startswith("확정") or r["상태"].startswith("실측 확정"))
    first = sum(1 for r in rows if r["실측값"].strip())
    text = f"PSD60 실측 확정 {done} / {len(rows)}"
    if first:
        text += f" · 1차 기록 {first}항목"
    return pill("ok" if done == len(rows) else "wait", text)


# ---------------------------------------------------------------- sections
def sec_open(s, ctx):
    src = f'<p class="src">{ctx.text(s["src"])}</p>' if s.get("src") else ""
    return f'<section id="{s["id"]}">{src}<h2>{ctx.text(s["title"])}</h2>'


def lines_block(ctx, check=None, fix=None):
    out = ""
    for lab, cls, val in (("확인", "lb", check), ("안 맞으면", "lb fx", fix)):
        for v in ([val] if isinstance(val, str) else (val or [])):
            out += f'<div><span class="{cls}">{lab}</span><span>{ctx.text(v)}</span></div>'
    return f'<div class="lines">{out}</div>' if out else ""


def body_block(ctx, item):
    out = ""
    if item.get("text"):
        out += ctx.text(item["text"]) if isinstance(item["text"], list) else f"<p>{ctx.text(item['text'])}</p>"
    if item.get("list"):
        out += "<ul>" + "".join(f"<li>{ctx.text(x)}</li>" for x in item["list"]) + "</ul>"
    return out


def s_summary(s, ctx):
    cards = ""
    for c in s["cards"]:
        inner = f'<span class="k">{ctx.text(c["k"])}</span>'
        if c.get("big"):
            inner += f'<span class="big">{ctx.text(c["big"])}</span>'
        if c.get("text"):
            inner += f"<p>{ctx.text(c['text'])}</p>"
        if c.get("ol"):
            inner += "<ol>" + "".join(f"<li>{ctx.text(x)}</li>" for x in c["ol"]) + "</ol>"
        cards += f"<div>{inner}</div>"
    return sec_open(s, ctx) + f'<div class="sum">{cards}</div></section>'


def s_structure(s, ctx):
    lis = "".join(f'<li style="--sw:{l["color"]}"><span class="z">{ctx.text(l["z"])}</span>'
                  f'<span><b>{ctx.text(l["title"])}</b> {ctx.text(l["text"])}</span></li>' for l in s["layers"])
    body = f'<ol class="layers">{lis}</ol>'
    if s.get("note"):
        body += f'<p class="note">{ctx.text(s["note"])}</p>'
    body += figs(ctx, s.get("figs"), s.get("cols", 2))
    return sec_open(s, ctx) + f'<div class="stack">{body}</div></section>'


def s_fit(s, ctx):
    intro = "".join(f"<p>{ctx.text(p)}</p>" for p in s.get("intro", []))
    if s.get("note"):
        intro += f'<p class="note">{ctx.text(s["note"])}</p>'
    rows = ""
    for r in s["rows"]:
        def cell(main, sub):
            out = f'<span class="num">{ctx.text(main)}</span>' if r.get("numeric", True) else ctx.text(main)
            return out + (f"<small>{ctx.text(sub)}</small>" if sub else "")
        rows += (f"<tr><td>{ctx.text(r['where'])}</td><td>{cell(r['worst'], r.get('worst_sub'))}</td>"
                 f"<td>{cell(r['absorb'], r.get('absorb_sub'))}</td><td>{pill(r['tone'], ctx.text(r['verdict']))}</td>"
                 f"<td>{ctx.text(r['fix'])}</td></tr>")
    table = ('<div class="tbl wide"><table><thead><tr><th style="width:16%">맞닿는 곳</th><th style="width:19%">최악 어긋남</th>'
             '<th style="width:22%">설계가 흡수하는 양</th><th style="width:12%">판정</th><th>안 맞으면</th></tr></thead>'
             f"<tbody>{rows}</tbody></table></div>")
    return (sec_open(s, ctx) + f'<div class="stack"><div class="prose">{intro}</div>{table}'
            + figs(ctx, s.get("figs"), s.get("cols", 2)) + "</div></section>")


def progress(group, label, reset=False):
    btn = '<button type="button" class="reset" id="reset">체크 초기화</button>' if reset else ""
    return (f'<div class="progress"><span id="p-{group}" data-label="{label}">{label} 0 / 0</span>'
            f'<span class="meter"><i id="m-{group}"></i></span>{btn}</div>')


def s_issues(s, ctx):
    items = ""
    for it in s["items"]:
        items += (f'<li class="issue"><div class="head">{pill(it["tone"], ctx.text(it["tag"]))}<h3>{ctx.text(it["title"])}</h3></div>'
                  f'<label class="tick"><input type="checkbox" id="rv-{it["id"]}"> 검토함</label>'
                  f'<p>{ctx.text(it["text"])}</p></li>')
    return (sec_open(s, ctx) + progress("review", "검토")
            + f'<ul class="issues" data-group="review">{items}</ul></section>')


def s_parts(s, ctx):
    rows, thin, small = "", [], []
    for p in s["printed"]:
        for b in p["bodies"]:
            if b not in ctx.bodies:
                die(f"parts: unknown body {b}")
        vol = sum(ctx.bodies[b]["volume_mm3"] for b in p["bodies"]) / 1000
        dims = ctx.dims(p["bodies"][0])
        size = " × ".join(f"{x:.0f}" for x in dims)
        d = sorted(dims, reverse=True)
        if d[0] < 30 or d[1] < 30:
            small.append(tag_strip(ctx.text(p["label"])))
        elif d[2] < 10:
            thin.append(tag_strip(ctx.text(p["label"])))
        rows += (f"<tr><td>{ctx.text(p['label'])}<small><code>{html.escape(', '.join(p['bodies']))}</code></small></td>"
                 f'<td class="num">{p.get("qty", 1)}</td><td class="num">{vol:.1f} cm³</td><td class="num">{size}</td>'
                 f"<td>{ctx.text(p.get('orient', ''))}</td><td>{ctx.text(p.get('note', ''))}</td></tr>")
    total = sum(ctx.bodies[b]["volume_mm3"] for p in s["printed"] for b in p["bodies"]) / 1000
    printed = ('<div class="tbl wide"><table><thead><tr><th>출력 부품</th><th>수량</th><th>부피</th><th>X × Y × Z mm</th>'
               f'<th>출력 방향</th><th>내용</th></tr></thead><tbody>{rows}</tbody></table></div>')
    auto_note = f"부피와 크기는 모델에서 읽은 값이다(합계 {total:.1f} cm³)."
    if small:
        auto_note += f" JLC3DP 최소 부품 크기 30 × 30 × 10보다 작은 부품: {', '.join(small)}."
    if thin:
        auto_note += f" 두께가 10보다 얇은 부품: {', '.join(thin)}."
    auto_note += " 접수 가능 여부를 업체에 확인한다."
    hw_rows = "".join(f"<tr><td>{ctx.text(h['item'])}</td><td class=\"num\">{ctx.text(h['qty'])}</td>"
                      f"<td>{ctx.text(h['spec'])}</td><td>{ctx.text(h['decide'])}</td></tr>" for h in s["hardware"])
    hardware = ('<div class="tbl mid"><table><thead><tr><th>구매품</th><th>수량</th><th>규격·후보</th><th>정할 것</th></tr></thead>'
                f"<tbody>{hw_rows}</tbody></table></div>")
    tools = f'<p class="note">{ctx.text(s["tools"])}</p>' if s.get("tools") else ""
    return (sec_open(s, ctx) + f'<div class="stack">{printed}<p class="note">{auto_note}</p>{hardware}{tools}</div></section>')


def diagram_block(ctx, item):
    figs = ""
    for gid in item.get("diagrams", []):
        for d in ctx.diagrams[gid]:
            cap = html.escape(d["caption"])
            wide = ' class="wide"' if d["wide"] else ""
            figs += (f'<figure{wide}><a href="{d["path"]}"><img src="{d["path"]}" width="{d["width"]}" '
                     f'height="{d["height"]}" loading="lazy" alt="{cap}"></a><figcaption>{cap}</figcaption></figure>')
    return f'<div class="diagrams">{figs}</div>' if figs else ""


def step_li(ctx, st, n, group, checkbox=True):
    head = f"<h3>{ctx.text(st['title'])}</h3>"
    if checkbox:
        head += f'<label class="tick"><input type="checkbox" id="as-{st["id"]}"> 완료</label>'
    body = body_block(ctx, st) + lines_block(ctx, st.get("check"), st.get("fix"))
    if st.get("render"):
        inner = (f'<div class="sgrid fig"><div class="sbody">{body}</div>'
                 f'{figure(ctx, st["render"], st.get("caption"), st.get("alt"))}</div>')
    else:
        inner = body
    inner += diagram_block(ctx, st)
    return (f'<li class="step"><span class="no">{n:02d}</span><div class="sbody">'
            f'<div class="shead">{head}</div>{inner}</div></li>')


def s_assembly(s, ctx):
    out = sec_open(s, ctx)
    if s.get("callout"):
        out += f'<div class="callout"><p>{ctx.text(s["callout"])}</p></div>'
    out += f'<div style="margin-top:1.25rem">{progress("asm", "완료", reset=True)}</div>'
    n = 0
    for ph in s["phases"]:
        out += f'<p class="phase">{ctx.text(ph["title"])}</p><ol class="steps" data-group="asm">'
        for st in ph["steps"]:
            n += 1
            out += step_li(ctx, st, n, "asm")
        out += "</ol>"
    return out + "</section>"


def s_steps(s, ctx):
    lis = ""
    for i, st in enumerate(s["steps"], 1):
        lis += step_li(ctx, dict(st, id=f"{s['id']}-{i}"), i, None, checkbox=False)
    intro = f'<p class="note">{ctx.text(s["intro"])}</p>' if s.get("intro") else ""
    return sec_open(s, ctx) + f'<div class="stack">{intro}<ol class="steps">{lis}</ol></div></section>'


def s_table(s, ctx):
    head = "".join(f"<th>{ctx.text(c)}</th>" for c in s["columns"])
    rows = ""
    for r in s["rows"]:
        cells = []
        for c in r:
            if isinstance(c, dict) and "tone" in c:
                cells.append(f"<td>{pill(c['tone'], ctx.text(c['text']))}</td>")
            else:
                cells.append(f"<td>{ctx.text(c)}</td>")
        rows += "<tr>" + "".join(cells) + "</tr>"
    intro = f'<p class="note">{ctx.text(s["intro"])}</p>' if s.get("intro") else ""
    cls = s.get("width", "mid")
    return (sec_open(s, ctx) + f'<div class="stack">{intro}<div class="tbl {cls}"><table><thead><tr>{head}</tr></thead>'
            f"<tbody>{rows}</tbody></table></div></div></section>")


def s_measurements(s, ctx):
    cards = ""
    for r in ctx.mrows:
        mid = r["id"]
        name = s.get("names", {}).get(mid) or html.escape(r["항목"][:18])
        if mid in s.get("pills", {}):
            tone, text = s["pills"][mid]
        elif r["실측값"].strip():
            tone, text = "warn", "1차 기록"
        elif "생략" in r["상태"]:
            tone, text = "ok", html.escape(r["상태"])
        else:
            tone, text = "wait", html.escape(r["상태"] or "미확정")
        cards += f'<div class="m"><span class="id">{mid}</span><span class="nm">{ctx.text(name)}</span>{pill(tone, ctx.text(text))}</div>'
    note = f'<p class="note">{ctx.text(s["note"])}</p>' if s.get("note") else ""
    return sec_open(s, ctx) + f'<div class="stack">{note}<div class="mgrid" aria-label="실측 항목">{cards}</div></div></section>'


def s_log(s, ctx):
    def ul(items, rejected=False):
        cls = ' class="x"' if rejected else ""
        return ('<ul class="log">' + "".join(
            f'<li{cls}><span class="d">{ctx.text(i.get("date", "버린 안"))}</span><span><b>{ctx.text(i["title"])}</b> {ctx.text(i["text"])}</span></li>'
            for i in items) + "</ul>")
    return (sec_open(s, ctx) + f'<div class="figs" style="align-items:start">{ul(s["decisions"])}'
            f'{ul(s.get("rejected", []), True)}</div></section>')


SECTIONS = {"summary": s_summary, "structure": s_structure, "fit": s_fit, "issues": s_issues, "parts": s_parts,
            "assembly": s_assembly, "steps": s_steps, "table": s_table, "measurements": s_measurements, "log": s_log}


# ---------------------------------------------------------------- page
def build_page(spec, ctx, model_name, model_sha, n_renders):
    pg = spec["page"]
    ev = ctx.ev
    errors = sum(1 for t in ev["timeline"] if t.get("error"))
    warnings = sum(1 for t in ev["timeline"] if t.get("warning"))
    dof_ok = all(s.get("dof") == 0 for s in ev["sketches"])
    chips = ""
    for c in pg.get("chips", []):
        if c.get("auto") == "measurements":
            chips += measurement_chip(ctx.mrows)
        elif c.get("auto") == "model":
            chips += pill("ok" if errors == 0 else "risk", f"모델 바디 {ev['body_count']} · 오류 {errors}")
        else:
            chips += pill(c["tone"], ctx.text(c["text"]))
    legend = "".join(f'<span><i style="background:{l["color"]}"></i>{ctx.text(l["label"])}</span>' for l in pg.get("legend", []))
    callout = f'<div class="callout" style="margin-top:1.1rem"><p>{ctx.text(pg["callout"])}</p></div>' if pg.get("callout") else ""
    hero = f'<div class="hero">{figure(ctx, pg["hero"], pg.get("hero_caption"), eager=True)}</div>' if pg.get("hero") else ""
    interactive = bool(spec.get('interactive'))
    nav = ('<a href="#interactive">3D 조립</a>' if interactive else '') + "".join(f'<a href="#{s["id"]}">{ctx.text(s.get("nav", s["title"]))}</a>' for s in spec["sections"])
    body = "".join(SECTIONS[s["type"]](s, ctx) for s in spec["sections"])
    stamp = datetime.date.today().isoformat()
    auto_foot = (f"모델 <code>{html.escape(model_name)}</code>(SHA-256 {model_sha[:12]}): 바디 {ev['body_count']}, "
                 f"피처 {len(ev['timeline'])}, 스케치 {len(ev['sketches'])}{'개 모두 dof 0' if dof_ok else ''}, "
                 f"타임라인 오류 {errors}, 경고 {warnings}. 렌더 {n_renders}장과 부품 표는 이 모델에서 자동으로 만들었다"
                 f"(생성 {stamp}).")
    foot = "".join(f"<p>{ctx.text(p)}</p>" for p in spec.get("footer", [])) + f"<p>{auto_foot}</p>"
    robots = '<meta name="robots" content="noindex, nofollow">\n' if pg.get("noindex") else ""
    mark = pg.get("mark", ["46", "es"])
    css = (HERE / "assets" / "guide.css").read_text(encoding="utf-8")
    js = (HERE / "assets" / "guide.js").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="ko" data-theme="light" data-store="{html.escape(pg.get('store_key', '46es-guide'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(pg['title'])}</title>
<meta name="description" content="{html.escape(pg['description'])}">
{robots}{FONTS}
<style>
{css}</style>
{('<link rel="stylesheet" href="assembly.css">' if interactive else '')}
</head>
<body>
<header class="wrap mast">
  <div class="mast-top"><div class="mark" aria-hidden="true">{mark[0]}<span>{mark[1]}</span></div><h1>{ctx.text(pg['h1'])}</h1></div>
  <p class="sub">{ctx.text(pg['sub'])}</p>
  <p class="lede">{ctx.text(pg['lede'])}</p>
  <div class="chips">{chips}</div>
  {callout}
  <div class="legend" aria-label="렌더 색 구분">{legend}</div>
  {hero}
</header>
<div class="bar"><div class="wrap"><nav aria-label="섹션">{nav}</nav></div></div>
<main class="wrap">
{assembly.markup(getattr(ctx, 'interactive', None)) if interactive else ''}
<details id="reference-docs" class="reference-docs"><summary>상세 설계 · 전체 조립 순서 · 시험 항목</summary>
{body}
</details>
</main>
<footer class="wrap">{foot}</footer>
<script>
{js}</script>
{('<script type="module" src="assembly.js"></script>' if interactive else '')}
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", default="guide_v5.json")
    ap.add_argument("--out", help="output directory (default: out, or out_assembly_review in assembly-only mode)")
    ap.add_argument("--cli", default=str(DEFAULT_CLI))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--skip-renders", action="store_true", help="use cached renders only, fail if one is missing")
    ap.add_argument("--only", default="", help="comma-separated render ids to (re)build; others must be cached")
    ap.add_argument("--clean-img", action="store_true", help="delete PNGs in OUT/img that this build does not use")
    ap.add_argument("--assembly-only", action="store_true", help="build a local assembly review without the static CAD snapshots")
    a = ap.parse_args()

    spec_path = (HERE / a.spec).resolve() if not Path(a.spec).is_absolute() else Path(a.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    model = (base / spec["model"]).resolve()
    out = HERE / (a.out or ("out_assembly_review" if a.assembly_only else "out"))
    cli = Path(a.cli)
    if not model.exists():
        die(f"model not found: {model}")
    if not cli.exists():
        die(f"SolidCraft CLI not found: {cli} (use --cli)")

    model_sha = file_sha256(model)
    if spec.get('reference_manifest'):
        manifest_path = (base / spec['reference_manifest']).resolve()
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        reference_root = manifest_path.parent
        generator = manifest['generator']
        inputs = [(reference_root / manifest['source'], 'source_sha'),
                  (reference_root / 'measurements/2026-11-04T111846Z.json', 'measurement_sha'),
                  (reference_root.parent / generator, 'generator_sha'),
                  (model, 'output_sha')]
        if any(file_sha256(path) != manifest[key] for path, key in inputs):
            die(f'assembly reference is stale; run python {generator} first')
    ev = model_eval(cli, model, model_sha)
    names = [b["name"] for b in ev["bodies"]]
    groups = spec.get("groups", {})
    ctx = Ctx(spec, ev, names, groups)
    ctx.mrows = measurements((base / spec["measurements"]).resolve())

    renders = [] if a.assembly_only else spec["renders"]
    looks = body_looks(model) if renders else {}
    ids = [r["id"] for r in renders]
    if len(set(ids)) != len(ids):
        die("duplicate render ids")
    only = {x for x in a.only.split(",") if x}
    defaults = spec.get("render_defaults", {"camera": "iso", "size": [1400, 620]})
    unknown = only - set(ids)
    if unknown:
        die(f"--only: unknown render ids {sorted(unknown)}")
    results = {}
    for r in renders:
        ctx.sizes[r["id"]] = r.get("size", defaults["size"])
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        futs = {}
        for r in renders:
            cached_only = a.skip_renders or bool(only and r["id"] not in only)
            futs[ex.submit(render_job, cli, model, looks, r, names, groups, spec["cameras"], defaults,
                           cached_only)] = r["id"]
        fresh = 0
        for f in cf.as_completed(futs):
            rid, png, made = f.result()
            results[rid] = png
            fresh += made
            print(f"render {rid}: {'new' if made else 'cached'}", flush=True)

    img = out / "img"
    img.mkdir(parents=True, exist_ok=True)
    for rid, png in results.items():
        shutil.copyfile(png, img / f"{rid}.png")
    if a.clean_img:
        for p in img.glob("*.png"):
            if p.stem not in results:
                p.unlink()
                print(f"removed unused {p.name}")
    ctx.diagrams = diagrams.build(out, ctx)
    for section in spec["sections"]:
        for st in [s for ph in section.get("phases", []) for s in ph["steps"]] + section.get("steps", []):
            unknown = set(st.get("diagrams", [])) - set(ctx.diagrams)
            if unknown:
                die(f"step {st.get('id', st.get('title'))}: unknown diagrams {sorted(unknown)}")
    assembly.prepare(ctx, base, out, cli, model, model_sha, CACHE, expand, run, die,
                     assembly_only=a.assembly_only)
    page_spec = spec
    if a.assembly_only:
        section = next(section for section in spec['sections'] if section['type'] == 'assembly')
        phases = [dict(phase, steps=[dict(step, render=None) for step in phase['steps']])
                  for phase in section['phases']]
        page_spec = dict(spec, sections=[dict(section, phases=phases)],
                         page=dict(spec['page'], hero=None, noindex=True,
                                   lede='조립 시각 검토용 · 현재 CAD의 3D 모델과 조립도를 표시합니다.'))
    page = build_page(page_spec, ctx, model.name, model_sha, len(results))
    (out / "index.html").write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {out / 'index.html'} ({len(page.encode('utf-8'))} bytes), {len(results)} images, {fresh} rendered now")


if __name__ == "__main__":
    main()
