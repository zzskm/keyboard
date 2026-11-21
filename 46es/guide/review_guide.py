"""Build the current motion guide and capture manual STEP 1-6 + 36s key frames + underside view for visual review."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import mkdtemp
from threading import Thread

from build_guide import DEFAULT_CLI, file_sha256

HERE = Path(__file__).resolve().parent
CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
MOTION_KEYFRAMES = (
    ('t00-0s-idle', 0.0),
    ('t01-8s-dims', 1.8),
    ('t03-4s-explode', 3.4),
    ('t07-6s-hero-bolts', 7.6),
    ('t10-7s-hold', 10.7),
    ('t14-0s-xray', 14.0),
    ('t18-0s-core', 18.0),
    ('t22-2s-seat-warn', 22.2),
    ('t24-2s-seat-ok', 24.2),
    ('t29-5s-bom', 29.5),
    ('t35-5s-report', 35.5),
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def capture(site, evidence, steps, views):
    from playwright.sync_api import sync_playwright

    handler = partial(QuietHandler, directory=str(site))
    with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=os.environ.get('BROWSER_EXECUTABLE', CHROME),
                    args=['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
                )
                page = browser.new_page(viewport={'width': 1920, 'height': 1080}, reduced_motion='reduce')
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.wait_for_function("document.documentElement.dataset.motionReady === '1'", timeout=120000)

                captures = []
                if 'motion' in views:
                    frame_images = []
                    for label, t_sec in MOTION_KEYFRAMES:
                        page.evaluate('(t) => window.__motionControl.seek(t)', t_sec)
                        page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
                        name = f'motion-{label}.png'
                        page.locator('#motion-stage').screenshot(path=evidence / name)
                        frame_images.append(name)

                    # Underside + CASE OFF inspection capture
                    page.evaluate('() => { window.__motionControl.seek(0); window.__motionControl.setLayer("case", false); window.__motionControl.setPreset("bottom", 0); }')
                    page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
                    btm_name = 'motion-case-off-btm.png'
                    page.locator('#motion-stage').screenshot(path=evidence / btm_name)
                    frame_images.append(btm_name)
                    page.evaluate('() => window.__motionControl.resetView()')
                    page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')

                    captures.append({'id': 'timeline', 'title': '36.0s technical motion sequence + underside inspection', 'images': frame_images})

                for step_num, step_code in steps:
                    page.locator(f'.step-btn[data-step="{step_num}"]').click()
                    page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
                    name = f'step{step_num}-{step_code}.png'
                    page.locator('#motion-stage').screenshot(path=evidence / name)
                    captures.append({'id': f'step{step_num}', 'title': step_code, 'images': [name]})

                if errors:
                    raise RuntimeError('browser errors: ' + '; '.join(errors))
                browser.close()
                return captures
        finally:
            server.shutdown()
            thread.join()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps', nargs='+', default=['step1', 'step2', 'step3', 'step4', 'step5', 'step6'],
                        help='manual step IDs (step1..step6)')
    parser.add_argument('--views', nargs='+', choices=('motion', 'steps-only'), default=['motion'],
                        help='motion = capture 36s keyframes + underside + requested steps; steps-only = steps only')
    parser.add_argument('--cli', default=str(DEFAULT_CLI))
    args = parser.parse_args()

    spec = json.loads((HERE / 'guide_v5.json').read_text(encoding='utf-8'))
    config = json.loads((HERE / spec['interactive']).read_text(encoding='utf-8'))
    valid_map = {f'step{i}': (i, s['code']) for i, s in enumerate(config['steps'], 1)}
    unknown = sorted(set(args.steps) - set(valid_map))
    if unknown:
        parser.error('unknown step(s): ' + ', '.join(unknown) + '. Available: ' + ', '.join(valid_map))
    steps = [valid_map[s] for s in valid_map if s in args.steps]

    manifest_path = (HERE / spec['reference_manifest']).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    source = manifest_path.parent / manifest['source']
    model = HERE / spec['model']
    source_sha, model_sha = file_sha256(source), file_sha256(model)
    runs = HERE / '.cache' / 'visual-review'
    runs.mkdir(parents=True, exist_ok=True)
    evidence = Path(mkdtemp(dir=runs))
    print(f'Visual review files: {evidence}', flush=True)
    site = evidence / 'site'
    subprocess.run([sys.executable, '-B', str(HERE / 'build_guide.py'),
                    '--assembly-only', '--out', str(site), '--cli', args.cli], check=True)
    built = json.loads((site / 'assembly.json').read_text(encoding='utf-8'))
    if built['model_sha'] != model_sha or file_sha256(model) != model_sha or file_sha256(source) != source_sha:
        raise RuntimeError('CAD changed during guide build; rerun visual review')
    if len(built['steps']) != len(config['steps']):
        raise RuntimeError('built guide step count differs from assembly_v5.json')

    captures = capture(site, evidence, steps, args.views)
    report = {
        'status': 'pending_manual_review',
        'source_sha256': source_sha,
        'review_model_sha256': model_sha,
        'spec_sha256': {name: file_sha256(HERE / name) for name in ('guide_v5.json', spec['interactive'])},
        'steps': captures,
    }
    (evidence / 'review.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Inspect the captures and record the visual verdict in the change report.')


if __name__ == '__main__':
    main()
