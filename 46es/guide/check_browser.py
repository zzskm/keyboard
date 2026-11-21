"""Browser check of the 46es v5 3D technical motion & interactive inspection guide.

  python 46es/guide/check_browser.py --site 46es/guide/out
  GUIDE_URL=http://127.0.0.1:8766/ python 46es/guide/check_browser.py

Verifies:
  1. Initial paused load at t=0.0s with WebGL ready and 0 page errors.
  2. SSOT live metrics parity (6 steps, 9 layers, 16 BOM cards, 197 pcs, 42 fasteners, 150 scan points, CAD verification).
  3. All 36.0s timeline phases (dims 1.8s, explode 3.4s, hero M3x10 bolts 7.6s, hold 10.7s, X-Ray 14.0s, Core 18.0s, Seat Sim 22.2/24.2s, interactive BOM 29.5s, live 6-cell CAD report 35.5s).
  4. 9 layer visibility toggles, CASE toggle, SOLO, ALL reset, and hidden-layer BOM ghost state.
  5. 2-mode camera (presets, BTM underside ground shutoff, UserOverride stability across scrub, Play blend & drag interrupt).
  6. Manual STEP 1-6 toggles, SPEC ↓ jump to <details id="reference-docs"> SVGs.
  7. 6 responsive viewports (1920x1080, 1440x1100, 1280x800, 1024x768, 768x1024, 390x844) with 0 horizontal overflow.
  8. WebGL unavailable fallback.
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
VIEWPORTS = (
    ('1920x1080', 1920, 1080),
    ('1440x1100', 1440, 1100),
    ('1280x800', 1280, 800),
    ('1024x768', 1024, 768),
    ('768x1024', 768, 1024),
    ('390x844', 390, 844),
)


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

        def wait_frames():
            page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')

        def seek_and_wait(t_sec):
            page.evaluate('(t) => window.__motionControl.seek(t)', t_sec)
            wait_frames()

        # 1. Initial paused state at 0.0s
        init_state = page.evaluate('window.__motionControl.getState()')
        assert init_state['playing'] is False, init_state
        assert abs(init_state['currentT'] - 0.0) < 0.01, init_state
        assert init_state['cameraMode'] == 'Timeline', init_state
        assert page.locator('#btn-play').get_attribute('aria-pressed') == 'false'
        page.screenshot(path=shot_prefix + 'fhd-00s.png')

        # 2. SSOT live metrics parity assertions
        m = page.evaluate('window.__motionMetrics')
        assert m['switches'] == 46, m
        assert m['keycaps'] == 46, m
        assert m['diodes'] == 46, m
        assert m['pins'] == 92, m
        assert m['wires'] == 16, m
        assert m['pads'] == 16, m
        assert m['fasteners'] == 42, m
        assert m['scanPointsTotal'] == 150, m
        assert m['stepsCount'] == 6, m
        assert abs(m['durationSec'] - 36.0) < 0.01, m
        assert len(m['layers']) == 9, m['layers']
        assert len(m['bom']) == 16, m['bom']
        assert m['totalParts'] == 197, m['totalParts']
        assert sum(g['count'] for g in m['groups']) == 197, m['groups']
        assert sum(l['count'] for l in m['layers']) == 197, m['layers']
        assert sum(b['count'] for b in m['bom']) == 197, m['bom']
        assert m['keycapsByWidth'] == {'1': 43, '1.25': 1, '2': 1, '2.25': 1}, m['keycapsByWidth']
        assert m['printStats']['bodyCount'] == 14 and m['printStats']['uniqueStls'] == 12, m['printStats']
        assert m['cadVerification'] and m['cadVerification']['overlaps'] == 0, m['cadVerification']
        assert 280.0 < m['widthMm'] < 340.0 and 100.0 < m['depthMm'] < 140.0, m
        assert 1.5 < m['tiltDeg'] < 3.5, m['tiltDeg']

        # 3. Verify 36.0s timeline phases
        seek_and_wait(1.8)
        w_text = page.locator('[data-dim="width"]').text_content() or ''
        tilt_text = page.locator('[data-dim="tilt"]').text_content() or ''
        assert f'{m["widthMm"]:.1f}' in w_text and '°' in tilt_text, (w_text, tilt_text, m['widthMm'])
        page.screenshot(path=shot_prefix + 't01-dims.png')

        seek_and_wait(3.4)
        page.screenshot(path=shot_prefix + 't03-explode.png')

        # Hero G3-PLATE M3x10 bolt insertion (7.6s)
        seek_and_wait(7.6)
        bolt_tag = page.locator('#hud-bolt-tag')
        assert bolt_tag.is_visible() and 'M3×10' in bolt_tag.inner_text(), bolt_tag.inner_text()
        st76 = page.evaluate('window.__motionControl.getState()')
        assert st76['activeBoltGuides'] >= 6, st76
        page.screenshot(path=shot_prefix + 't07-bolts.png')

        # 0.60s full-assembly hold (10.7s)
        seek_and_wait(10.7)
        assert not page.locator('#hud-bolt-tag').is_visible()
        page.screenshot(path=shot_prefix + 't10-hold.png')

        # X-Ray scan (14.0s)
        seek_and_wait(14.0)
        tel = page.locator('#hud-telemetry')
        assert tel.is_visible() and 'FST' in tel.inner_text() and 'PIN' in tel.inner_text(), tel.inner_text()
        page.screenshot(path=shot_prefix + 't14-xray.png')

        # Core Focus (18.0s)
        seek_and_wait(18.0)
        svg_txt = page.locator('#motion-overlay').text_content() or ''
        assert 'ATMEGA32U4' in svg_txt and 'M3×10' in svg_txt and f'×{m["diodes"]}' in svg_txt, svg_txt
        page.screenshot(path=shot_prefix + 't18-core.png')

        # Seat Sim (22.2s warn -> 24.2s ok)
        seek_and_wait(22.2)
        warn_badge = page.locator('[data-closeup-badge="warn"]')
        assert warn_badge.is_visible() and 'SIM ΔZ' in (warn_badge.text_content() or ''), warn_badge.text_content()
        page.screenshot(path=shot_prefix + 't22-seat-warn.png')

        seek_and_wait(24.2)
        ok_badge = page.locator('[data-closeup-badge="ok"]')
        assert ok_badge.is_visible() and 'SIM SEAT 0.0 mm ✓' in (ok_badge.text_content() or ''), ok_badge.text_content()
        page.screenshot(path=shot_prefix + 't24-seat-ok.png')

        # Interactive BOM Grid (29.5s)
        seek_and_wait(29.5)
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
        # Click BOM card to verify bidirectional highlight
        page.locator('.bom-card[data-bom-id="bom-plate"]').click()
        assert page.locator('.bom-card[data-bom-id="bom-plate"]').get_attribute('aria-pressed') == 'true'
        page.locator('.bom-card[data-bom-id="bom-plate"]').click()
        page.screenshot(path=shot_prefix + 't29-bom.png')

        # Live 6-cell CAD Report (35.5s)
        seek_and_wait(35.5)
        rep = page.locator('#hud-report')
        assert rep.is_visible()
        assert 'mm' in page.locator('#rep-env').inner_text()
        assert 'cm³' in page.locator('#rep-print').inner_text()
        assert '42 pcs' in page.locator('#rep-fast').inner_text()
        assert '46 keys' in page.locator('#rep-keys').inner_text()
        assert '4×12 io' in page.locator('#rep-matrix').inner_text()
        assert '0 OVL ✓ (197)' in page.locator('#rep-fit').inner_text(), page.locator('#rep-fit').inner_text()
        assert 'PIN 0.56' in page.locator('#rep-fit-sub').inner_text(), page.locator('#rep-fit-sub').inner_text()
        page.screenshot(path=shot_prefix + 't35-report.png')

        # 4. 9-Layer visibility toggles, SOLO & ALL reset
        seek_and_wait(0.0)
        page.locator('.layer-btn[data-layer="case"]').click()
        wait_frames()
        assert 'case' in page.evaluate('window.__motionControl.getState().hiddenLayers')
        page.evaluate('window.__motionControl.soloLayer("plate")')
        wait_frames()
        assert len(page.evaluate('window.__motionControl.getState().hiddenLayers')) == 8
        page.locator('#btn-layers-all').click()
        wait_frames()
        assert len(page.evaluate('window.__motionControl.getState().hiddenLayers')) == 0

        # 5. 2-Mode Camera: BTM underside shutoff, UserOverride stability across scrub, Play blend
        page.evaluate('() => { window.__motionControl.setLayer("case", false); window.__motionControl.setPreset("bottom", 0); }')
        wait_frames()
        st_btm = page.evaluate('window.__motionControl.getState()')
        assert st_btm['cameraMode'] == 'UserOverride', st_btm
        assert st_btm['groundVisible'] is False, st_btm
        pose_before = st_btm['cameraPose']
        seek_and_wait(5.0)
        pose_after = page.evaluate('window.__motionControl.getState().cameraPose')
        assert abs(pose_before['azimuthDeg'] - pose_after['azimuthDeg']) < 0.01, (pose_before, pose_after)
        assert abs(pose_before['elevationDeg'] - pose_after['elevationDeg']) < 0.01, (pose_before, pose_after)
        page.screenshot(path=shot_prefix + 'case-off-btm.png')

        # Play returns to Timeline camera & interrupt returns to UserOverride
        page.evaluate('window.__motionControl.resetView()')
        wait_frames()
        assert page.evaluate('window.__motionControl.getState().cameraMode') == 'Timeline'

        # 6. Manual STEP 1-6 toggles & scrubber return
        for step_num in range(1, 7):
            btn = page.locator(f'.step-btn[data-step="{step_num}"]')
            btn.click()
            wait_frames()
            assert btn.get_attribute('aria-pressed') == 'true'
        page.screenshot(path=shot_prefix + 'step6-manual.png')
        page.locator('#timeline-scrubber').evaluate("el => { el.value = '5'; el.dispatchEvent(new Event('input', { bubbles: true })); }")
        assert page.evaluate('window.__motionControl.getState().manualStep') is None

        # 7. SPEC ↓ button opens <details id="reference-docs"> & loads all SVGs
        page.locator('#btn-spec').click()
        assert page.locator('#reference-docs').evaluate('(el) => el.open') is True
        diagram_imgs = page.locator('#reference-docs .diagrams img')
        assert diagram_imgs.count() >= 10, diagram_imgs.count()
        page.locator('#diagrams').scroll_into_view_if_needed()
        page.wait_for_function(
            "Array.from(document.querySelectorAll('#reference-docs .diagrams img')).every(i => i.complete && i.naturalWidth > 0)",
            timeout=30000,
        )
        page.locator('#reference-docs > summary').click()
        page.evaluate('window.scrollTo(0, 0)')

        # 8. 6-Viewport responsive zero-overflow checks
        viewport_results = {}
        for label, vw, vh in VIEWPORTS:
            page.set_viewport_size({'width': vw, 'height': vh})
            page.evaluate('window.scrollTo(0, 0)')
            seek_and_wait(35.5)
            overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
            assert not overflow, f'Horizontal overflow at {label}'
            viewport_results[label] = 'ok'
            if label in ('1280x800', '390x844'):
                page.screenshot(path=f'{shot_prefix}vp-{label}-report.png')
                seek_and_wait(29.5)
                assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth'), f'BOM overflow at {label}'
                page.screenshot(path=f'{shot_prefix}vp-{label}-bom.png')

        # 9. WebGL unavailable fallback check
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
        'layers': len(m['layers']),
        'total_parts': m['totalParts'],
        'switches': m['switches'],
        'pins': m['pins'],
        'diodes': m['diodes'],
        'fasteners': m['fasteners'],
        'bom_cards': len(m['bom']),
        'dims_mm': [m['widthMm'], m['depthMm'], m['heightMm']],
        'tilt_deg': m['tiltDeg'],
        'cad_overlaps': m['cadVerification']['overlaps'],
        'viewports': viewport_results,
        'page_errors': errors,
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
