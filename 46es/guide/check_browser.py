"""Browser check of a built guide: steps, parts, diagrams, 3D, fallback, saved progress, phone width.

  python guide/check_browser.py --site guide/out          # serve a build folder on a free local port
  GUIDE_URL=http://127.0.0.1:8766/ python guide/check_browser.py   # or check a running server
Counts come from the build's assembly.json, so adding a step does not need an edit here.
Needs Playwright and Chrome (BROWSER_EXECUTABLE overrides the path). Screenshots: GUIDE_SHOT_PREFIX.
"""
import argparse
import json
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(folder):
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(folder)))
    Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}/'


def run(base_url, shot_prefix, executable=None):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executable or os.environ.get('BROWSER_EXECUTABLE', CHROME), headless=True,
                                    args=['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base_url + '#interactive')
        page.locator('#assembly-ui').wait_for(state='visible', timeout=60000)
        data = page.evaluate("fetch('assembly.json').then(r=>r.json())")
        steps, parts = data['steps'], data['parts']
        ids = [s['id'] for s in steps]
        last = len(steps) - 1
        assert page.locator('#asm-step option').count() == len(steps)
        assert next(p for p in parts if p['id'] == 'keycaps')['mesh']
        assert len(next(p for p in parts if p['id'] == 'switches')['pieces']) == 4
        assert '부분 실측' in next(p for p in parts if p['id'] == 'housing')['label']
        controller = next(part for part in parts if part['id'] == 'controller')
        assert controller['preserveColors'] and len({piece['color'] for piece in controller['pieces']}) >= 5
        page.locator('#interactive').scroll_into_view_if_needed()
        page.screenshot(path=shot_prefix + 'desktop.png')
        diagrams = page.locator('#asm-diagrams')
        shown = 0
        for i, step in enumerate(steps):
            page.locator('#asm-step').select_option(str(i))
            assert page.locator('#asm-title').inner_text()
            assert page.locator('.assembly-part').count() > 0
            page.wait_for_function("document.querySelector('#asm-drawing').naturalWidth > 0")
            if step.get('diagrams'):
                diagrams.wait_for(state='visible')
                assert diagrams.locator('figure').count() == len(step['diagrams'])
                diagrams.scroll_into_view_if_needed()
                page.wait_for_function("Array.from(document.querySelectorAll('#asm-diagrams img')).every(img => img.complete && img.naturalWidth > 0)")
                shown += len(step['diagrams'])
            else:
                assert not diagrams.is_visible(), f'diagrams shown on {step["id"]}'
        assert shown >= 10, f'only {shown} diagrams shown'
        page.locator('#asm-step').select_option(str(ids.index('wire')))
        diagrams.locator('figure.wide').first.screenshot(path=shot_prefix + 'wiring-map.png')
        page.locator('#asm-step').select_option(str(last))
        page.locator('#asm-done').check()
        page.locator('#asm-3d').click()
        page.wait_for_function("document.getElementById('assembly-status').textContent.includes('3D 준비 완료')", timeout=120000)
        page.screenshot(path=shot_prefix + 'oem.png')
        page.locator('[data-view=front]').click()
        page.screenshot(path=shot_prefix + 'case-height.png')
        assert page.locator(f'#as-{ids[last]}').is_checked()
        page.reload()
        page.locator('#assembly-ui').wait_for(state='visible', timeout=60000)
        assert page.locator('#asm-step').input_value() == str(last)
        assert page.locator('#asm-done').is_checked()
        page.locator('.parts-catalog summary').first.click()
        page.locator('#asm-scope').select_option('all')
        assert page.locator('.assembly-part').count() == len(parts)
        page.locator('#asm-search').fill('NBK SSH-M2-5')
        assert page.locator('.assembly-part').count() == 1
        page.locator('#asm-search').fill('')
        page.locator('.part-select').first.click()
        page.locator('.assembly-part .tick input').first.check()
        page.reload()
        page.locator('#assembly-ui').wait_for(state='visible', timeout=60000)
        page.locator('.parts-catalog summary').first.click()
        page.locator('#asm-scope').select_option('all')
        assert page.locator('.assembly-part .tick input').first.is_checked()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('#asm-step').select_option(str(ids.index('wire')))
        page.wait_for_function('document.documentElement.scrollWidth <= innerWidth', timeout=10000)
        page.locator('#asm-diagrams').scroll_into_view_if_needed()
        page.screenshot(path=shot_prefix + 'mobile.png', full_page=False)
        page.locator('#mode-compare').click()
        page.locator('#cmp-scope').select_option('cover')
        page.wait_for_function("document.querySelector('#r2-fallback').getAttribute('src').endsWith('r2-cover.png')")
        page.wait_for_function("document.querySelector('#v5-fallback').naturalWidth > 0")
        page.locator('#cmp-3d').click()
        page.locator('#r2-canvas canvas').wait_for(state='visible', timeout=120000)
        page.locator('[data-compare-view=top]').click()
        assert page.locator('#v5-canvas canvas').is_visible()
        fallback = browser.new_page()
        fallback.route('**/viewer.js', lambda route: route.abort())
        fallback.goto(base_url + '#interactive')
        fallback.locator('#assembly-ui').wait_for(state='visible', timeout=60000)
        fallback.locator('#asm-step').select_option('0')
        fallback.locator('#asm-3d').click()
        fallback.wait_for_function("document.getElementById('assembly-status').textContent.includes('3D를 사용할 수 없습니다')")
        assert fallback.locator('#asm-drawing').is_visible()
        fallback.locator('#asm-next').click()
        assert fallback.locator('#asm-title').inner_text() == re.sub(r'<[^>]+>', '', steps[1]['title'])
        browser.close()
    result = {'steps': len(steps), 'parts': len(parts), 'diagrams': shown, 'page_errors': errors,
              'mobile_overflow': False, 'fallback': 'passed', 'persistence': 'passed'}
    assert not errors, errors
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--site', help='build folder to serve (default: use GUIDE_URL)')
    a = ap.parse_args()
    shots = os.environ.get('GUIDE_SHOT_PREFIX', str(Path(__file__).resolve().parent / '.cache' / 'assembly-'))
    Path(shots).parent.mkdir(parents=True, exist_ok=True)
    if a.site:
        server, url = serve(Path(a.site).resolve())
        try:
            result = run(url, shots)
        finally:
            server.shutdown()
    else:
        result = run(os.environ.get('GUIDE_URL', 'http://127.0.0.1:8766/'), shots)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
