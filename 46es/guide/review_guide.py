"""Build the current guide and capture selected assembly steps for visual review.

Per step: the 2D drawing, the step diagrams (wiring map, snap, ...) when it has any, and one 3D capture per --views.
"""
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
                page = browser.new_page(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')  # camera moves land in one frame
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/#interactive')
                page.locator('#asm-drawing').wait_for(state='visible')
                captures = []
                for index, step_id in steps:
                    page.locator('#asm-step').select_option(str(index))
                    title = page.locator('#asm-title').inner_text()
                    page.locator('#asm-drawing').evaluate('(image) => image.decode()')
                    drawing = f'{step_id}-drawing.png'
                    page.locator('#asm-drawing').screenshot(path=evidence / drawing)
                    images = [drawing]
                    diagrams = page.locator('#asm-diagrams')
                    if diagrams.is_visible():
                        page.wait_for_function("Array.from(document.querySelectorAll('#asm-diagrams img')).every(i => i.complete && i.naturalWidth > 0)")
                        images.append(f'{step_id}-diagrams.png')
                        diagrams.screenshot(path=evidence / images[-1])
                    page.locator('#asm-3d').click()
                    page.wait_for_function(
                        "document.getElementById('assembly-status').textContent.includes('3D 준비 완료')",
                        timeout=120000,
                    )
                    for view in views:
                        # section = the step's own cut (assembly_v5.json "section"), seen from its side
                        toggle = '#asm-section' if view == 'section' else f'[data-view={view}]'
                        page.locator(toggle).click()
                        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                        name = f'{step_id}-{view}.png'
                        page.locator('#asm-canvas').screenshot(path=evidence / name)
                        images.append(name)
                        if view == 'section':
                            page.locator('#asm-section').click()
                    page.locator('#asm-3d').click()
                    captures.append({'id': step_id, 'title': title, 'images': images})
                if errors:
                    raise RuntimeError('browser errors: ' + '; '.join(errors))
                browser.close()
                return captures
        finally:
            server.shutdown()
            thread.join()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps', nargs='+', required=True, help='assembly step IDs; the final step is included')
    parser.add_argument('--views', nargs='+', choices=('reset', 'iso', 'top', 'bottom', 'front', 'section'),
                        default=['iso'], help='reset = view of the step itself; iso/top/bottom/front = fixed views; '
                        'section = the step cut from assembly_v5.json (or one through its work parts)')
    parser.add_argument('--cli', default=str(DEFAULT_CLI))
    args = parser.parse_args()

    spec = json.loads((HERE / 'guide_v5.json').read_text(encoding='utf-8'))
    section = next(section for section in spec['sections'] if section['type'] == 'assembly')
    ids = [step['id'] for phase in section['phases'] for step in phase['steps']]
    unknown = sorted(set(args.steps) - set(ids))
    if unknown:
        parser.error('unknown step(s): ' + ', '.join(unknown) + '. Available: ' + ', '.join(ids))
    steps = [(index, step_id) for index, step_id in enumerate(ids)
             if step_id in args.steps or index == len(ids) - 1]

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
    assembly = json.loads((site / 'assembly.json').read_text(encoding='utf-8'))
    if assembly['model_sha'] != model_sha or file_sha256(model) != model_sha or file_sha256(source) != source_sha:
        raise RuntimeError('CAD changed during guide build; rerun visual review')
    if [step['id'] for step in assembly['steps']] != ids:
        raise RuntimeError('built guide step list differs from the requested spec')

    captures = capture(site, evidence, steps, args.views)
    report = {'status': 'pending_manual_review', 'source_sha256': source_sha,
              'review_model_sha256': model_sha,
              # tools/pipeline.py --status compares these with the working tree to tell whether a review is current
              'spec_sha256': {name: file_sha256(HERE / name) for name in ('guide_v5.json', spec['interactive'])},
              'steps': captures}
    (evidence / 'review.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Inspect the captures and record the visual verdict in the change report.')


if __name__ == '__main__':
    main()
