"""Browser check of the 46es v5 3D technical motion guide.

  python 46es/guide/check_browser.py --site 46es/guide/out
  GUIDE_URL=http://127.0.0.1:8766/ python 46es/guide/check_browser.py

Verifies:
  1. 1920x1080 & 1440x1100 load paused at t=0.0s with WebGL canvas ready and 0 page errors.
  2. Live metrics calculated from generated 3D objects match DOM readouts (dims, tilt, 46 switches, 92 pins, 46 diodes, 16 BOM cards).
  3. All 6 timeline segments (0-7s, 7-13s, 13-17s, 17-23s warn->ok, 23-29s BOM thumbnails, 29-32s 6-cell report).
  4. STEP 1-5 manual exploration toggles and return to scrubber.
  5. Collapsible <details id="reference-docs"> tables and all 7 diagrams.py SVG groups.
  6. Mobile (390x844) zero horizontal overflow & WebGL failure fallback.
"""
import argparse
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
READY = "document.documentElement.dataset.motionReady === '1'"


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
        browser = p.chromium.launch(
            executable_path=executable or os.environ.get('BROWSER_EXECUTABLE', CHROME),
            headless=True,
            args=['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
        )
        errors = []
        page = browser.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=1, reduced_motion='reduce')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base_url)
        page.wait_for_function(READY, timeout=120000)

        # 1. Initial paused state at 0.0s
        init_state = page.evaluate('window.__motionControl.getState()')
        assert init_state['playing'] is False, init_state
        assert abs(init_state['currentT'] - 0.0) < 0.01, init_state
        assert page.locator('#btn-play').get_attribute('aria-pressed') == 'false'
        page.screenshot(path=shot_prefix + 'fhd-00s.png')

        # 2. Live metrics assertions (zero hardcoding — derived from mounted 3D objects)
        m = page.evaluate('window.__motionMetrics')
        assert m['switches'] == 46, m
        assert m['keycaps'] == 46, m
        assert m['diodes'] == 46, m
        assert m['pins'] == 92, m
        assert m['wires'] == 16, m
        assert m['pads'] == 16, m
        assert m['fasteners'] == 42, m
        assert m['stepsCount'] == 5, m
        assert len(m['bom']) == 16, m
        assert m['keycapsByWidth'] == {'1': 43, '1.25': 1, '2': 1, '2.25': 1}, m['keycapsByWidth']
        assert sum(b['count'] for b in m['bom']) == m['totalParts'], m
        assert 280.0 < m['widthMm'] < 340.0 and 100.0 < m['depthMm'] < 140.0, m
        assert 1.5 < m['tiltDeg'] < 3.5, m['tiltDeg']

        def seek_and_wait(t_sec):
            page.evaluate('(t) => window.__motionControl.seek(t)', t_sec)
            page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')

        # 3. Verify all 6 timeline segments
        # 0-7s: bounding box + dimensions + explode
        seek_and_wait(1.8)
        w_text = page.locator('[data-dim="width"]').text_content() or ''
        tilt_text = page.locator('[data-dim="tilt"]').text_content() or ''
        assert 'mm' in w_text and '°' in tilt_text, (w_text, tilt_text)
        page.screenshot(path=shot_prefix + 't01-dims.png')

        seek_and_wait(3.4)
        page.screenshot(path=shot_prefix + 't03-explode.png')

        # 7-13s: X-Ray scan
        seek_and_wait(10.5)
        tel = page.locator('#hud-telemetry')
        assert tel.is_visible() and 'FST' in tel.inner_text() and 'PIN' in tel.inner_text(), tel.inner_text()
        page.screenshot(path=shot_prefix + 't10-xray.png')

        # 13-17s: Core focus + leader lines
        seek_and_wait(15.0)
        svg_txt = page.locator('#motion-overlay').text_content() or ''
        assert 'ATMEGA32U4' in svg_txt and f'×{m["diodes"]}' in svg_txt, svg_txt
        page.screenshot(path=shot_prefix + 't15-core.png')

        # 17-23s: Single-switch gap close-up (warn -> ok)
        seek_and_wait(19.2)
        warn_badge = page.locator('[data-closeup-badge="warn"]')
        assert warn_badge.is_visible() and '⚠' in (warn_badge.text_content() or ''), warn_badge.text_content()
        page.screenshot(path=shot_prefix + 't19-gap-warn.png')

        seek_and_wait(21.4)
        ok_badge = page.locator('[data-closeup-badge="ok"]')
        assert ok_badge.is_visible() and '0 ✓' in (ok_badge.text_content() or ''), ok_badge.text_content()
        page.screenshot(path=shot_prefix + 't21-gap-ok.png')

        # 23-29s: 16-card 3D BOM grid
        seek_and_wait(26.5)
        bom_box = page.locator('#hud-bom')
        assert bom_box.is_visible()
        assert page.locator('.bom-card').count() == 16
        all_thumbs_ok = page.evaluate(
            "Array.from(document.querySelectorAll('.bom-card img')).every(img => img.complete && img.naturalWidth > 0)"
        )
        assert all_thumbs_ok, 'one or more BOM 3D thumbnails failed to load'
        dom_bom_sum = page.evaluate(
            "Array.from(document.querySelectorAll('.bom-card')).reduce((a, el) => a + Number(el.dataset.count), 0)"
        )
        assert dom_bom_sum == m['totalParts'], (dom_bom_sum, m['totalParts'])
        page.screenshot(path=shot_prefix + 't26-bom.png')

        # 29-32s: 6-cell final build report
        seek_and_wait(31.5)
        rep = page.locator('#hud-report')
        assert rep.is_visible()
        assert page.locator('#rep-parts').inner_text() == str(m['totalParts'])
        assert page.locator('#rep-steps').inner_text() == '5'
        assert page.locator('#rep-groups').inner_text() == '5'
        assert page.locator('#rep-short').inner_text() == '0'
        assert '0 ✓' in page.locator('#rep-gap').inner_text()
        page.screenshot(path=shot_prefix + 't31-report.png')

        # 4. Manual STEP 1-5 toggles & scrubber return
        for step_num in range(1, 6):
            btn = page.locator(f'.step-btn[data-step="{step_num}"]')
            btn.click()
            page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
            assert btn.get_attribute('aria-pressed') == 'true'
        page.screenshot(path=shot_prefix + 'step5-manual.png')
        # Scrub back to timeline exits manual step mode
        page.locator('#timeline-scrubber').evaluate("el => { el.value = '5'; el.dispatchEvent(new Event('input', { bubbles: true })); }")
        assert page.evaluate('window.__motionControl.getState().manualStep') is None

        # 5. Collapsible <details id="reference-docs"> static tables & 7 diagrams.py SVGs
        page.locator('#reference-docs > summary').click()
        assert page.locator('#reference-docs').evaluate('(el) => el.open') is True
        diagram_imgs = page.locator('#reference-docs .diagrams img')
        assert diagram_imgs.count() >= 10, diagram_imgs.count()
        page.locator('#diagrams').scroll_into_view_if_needed()
        page.wait_for_function(
            "Array.from(document.querySelectorAll('#reference-docs .diagrams img')).every(i => i.complete && i.naturalWidth > 0)",
            timeout=30000,
        )

        # 6. Desktop 1440x1100 & Mobile 390x844 responsive overflow check
        page.locator('#reference-docs > summary').click()
        page.evaluate('window.scrollTo(0, 0)')
        page.set_viewport_size({'width': 1440, 'height': 1100})
        seek_and_wait(26.5)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')

        page.set_viewport_size({'width': 390, 'height': 844})
        page.evaluate('window.scrollTo(0, 0)')
        seek_and_wait(26.5)
        page.wait_for_function('document.documentElement.scrollWidth <= window.innerWidth', timeout=10000)
        page.screenshot(path=shot_prefix + 'mobile-bom.png')
        seek_and_wait(31.5)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=shot_prefix + 'mobile-report.png')

        # 7. WebGL unavailable fallback check
        fallback = browser.new_page(viewport={'width': 1280, 'height': 800})
        fallback.add_init_script("""
            const orig = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                if (type && type.includes('webgl')) return null;
                return orig.call(this, type, ...args);
            };
        """)
        fallback.goto(base_url)
        fallback.wait_for_function("document.documentElement.dataset.motionFallback === '1'", timeout=30000)
        assert fallback.locator('#motion-fallback').is_visible()
        assert fallback.locator('#reference-docs').evaluate('(el) => el.open') is True

        browser.close()

    assert not errors, errors
    return {
        'steps': m['stepsCount'],
        'total_parts': m['totalParts'],
        'switches': m['switches'],
        'pins': m['pins'],
        'diodes': m['diodes'],
        'bom_cards': len(m['bom']),
        'dims_mm': [m['widthMm'], m['depthMm'], m['heightMm']],
        'tilt_deg': m['tiltDeg'],
        'page_errors': errors,
        'mobile_overflow': False,
        'fallback': 'passed',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--site', help='build folder to serve (default: use GUIDE_URL)')
    a = ap.parse_args()
    shots = os.environ.get('GUIDE_SHOT_PREFIX', str(Path(__file__).resolve().parent / '.cache' / 'motion-'))
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
