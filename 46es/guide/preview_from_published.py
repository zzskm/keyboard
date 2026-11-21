#!/usr/bin/env python3
"""Build an explicitly labelled UI preview using hash-matched, already published assets.
No SolidCraft evaluation or new v5 rendering is claimed. Full publication uses build_guide.py.
Input folder needs assembly.json, models/, img/ from the existing published guide.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import assembly
import build_guide as guide

HERE = Path(__file__).resolve().parent


def build(source, out):
    spec = json.loads((HERE / 'guide_v5.json').read_text(encoding='utf-8'))
    config = json.loads((HERE / spec['interactive']).read_text(encoding='utf-8'))
    model = HERE / spec['model']
    data = json.loads((source / 'assembly.json').read_text(encoding='utf-8'))
    expected = hashlib.sha256(model.read_bytes()).hexdigest()
    if data['model_sha'] != expected:
        raise SystemExit('Published meshes are for a different CAD model; do not reuse.')
    out.mkdir(parents=True, exist_ok=True)
    for path in {piece['mesh'].split('#')[0] for part in data['parts'] for piece in part.get('pieces', [])}:
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, out / path)
    if (source / 'img').is_dir():
        shutil.copytree(source / 'img', out / 'img', dirs_exist_ok=True)
    (out / 'assembly.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8', newline='\n')
    assembly.copy_assets(out)
    css = (HERE / 'assets/guide.css').read_text(encoding='utf-8')
    fallback_hero = 'img/hero.png' if (out / 'img/hero.png').is_file() else ''
    page = (
        f'<!doctype html><html lang="ko" data-theme="light" data-store="46es-guide-v5"><head>'
        f'<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>46es v5 · Motion UI Preview</title><style>{css}</style>'
        f'<link rel="stylesheet" href="motion/motion.css"></head><body class="motion-page">'
        f'{assembly.markup(config, fallback_hero=fallback_hero)}'
        f'<div class="ref-shell"><details id="reference-docs" class="reference-docs">'
        f'<summary><span>UI PREVIEW</span><span class="ref-meta">model {expected[:12]}</span></summary>'
        f'<div class="ref-body wrap"><p>UI 검토본. v5 모델 해시 {expected[:12]}와 일치하는 게시 자산을 재사용했습니다.</p></div>'
        f'</details></div>'
        f'<script type="module" src="motion/controller.js"></script></body></html>\n'
    )
    (out / 'index.html').write_text(page, encoding='utf-8', newline='\n')
    print(f"UI preview: {out} · {len(data.get('steps', []))} steps · matching model {expected[:12]}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--published', type=Path, required=True)
    ap.add_argument('--out', type=Path, default=HERE / 'out_preview')
    a = ap.parse_args()
    build(a.published.resolve(), a.out.resolve())
