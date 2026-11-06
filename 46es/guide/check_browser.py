import json
import os
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get('GUIDE_URL', 'http://127.0.0.1:8766/')
SHOT = os.environ.get('GUIDE_SHOT_PREFIX', 'guide/.cache/assembly-')
SECOND_TITLE = os.environ.get('GUIDE_SECOND_STEP_TITLE', '커버·plate 자석 붙이기')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('BROWSER_EXECUTABLE', 'C:/Program Files/Google/Chrome/Application/chrome.exe'), headless=True, args=['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440,'height':1100}, device_scale_factor=1)
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE_URL)
    page.locator('#asm-drawing').wait_for(state='visible')
    assert page.locator('#asm-step option').count() == 15
    models = page.evaluate("fetch('assembly.json').then(r=>r.json()).then(d=>d.parts)")
    assert next(p for p in models if p['id']=='keycaps')['mesh']
    assert len(next(p for p in models if p['id']=='switches')['pieces']) == 4
    assert '부분 실측' in next(p for p in models if p['id']=='housing')['label']
    page.locator('#interactive').scroll_into_view_if_needed()
    page.screenshot(path=SHOT + 'desktop.png')
    for i in range(15):
        page.locator('#asm-step').select_option(str(i))
        assert page.locator('#asm-title').inner_text()
        assert page.locator('.assembly-part').count() > 0
        page.wait_for_function("document.querySelector('#asm-drawing').naturalWidth > 0")
    page.locator('#asm-done').check()
    page.locator('#asm-3d').click()
    page.wait_for_function("document.getElementById('assembly-status').textContent.includes('3D 준비 완료')", timeout=120000)
    page.screenshot(path=SHOT + 'oem.png')
    page.locator('[data-view=front]').click()
    page.screenshot(path=SHOT + 'case-height.png')
    assert page.locator('#as-keycap').is_checked()
    page.reload()
    page.locator('#asm-drawing').wait_for(state='visible')
    assert page.locator('#asm-step').input_value() == '14'
    assert page.locator('#asm-done').is_checked()
    page.locator('.parts-catalog summary').first.click()
    page.locator('#asm-scope').select_option('all')
    assert page.locator('.assembly-part').count() == 30
    page.locator('#asm-search').fill('NBK SSH-M2-5')
    assert page.locator('.assembly-part').count() == 1
    page.locator('#asm-search').fill('')
    page.locator('.part-select').first.click()
    page.locator('.assembly-part .tick input').first.check()
    page.reload()
    page.locator('#asm-drawing').wait_for(state='visible')
    page.locator('.parts-catalog summary').first.click()
    page.locator('#asm-scope').select_option('all')
    assert page.locator('.assembly-part .tick input').first.is_checked()
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#asm-step').select_option('9')
    page.wait_for_function('document.documentElement.scrollWidth <= innerWidth', timeout=10000)
    page.locator('#interactive').scroll_into_view_if_needed()
    page.screenshot(path=SHOT + 'mobile.png', full_page=False)
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
    fallback.goto(BASE_URL)
    fallback.locator('#asm-3d').click()
    fallback.wait_for_function("document.getElementById('assembly-status').textContent.includes('3D를 사용할 수 없습니다')")
    assert fallback.locator('#asm-drawing').is_visible()
    fallback.locator('#asm-next').click()
    assert fallback.locator('#asm-title').inner_text() == SECOND_TITLE
    print(json.dumps({'steps':15,'parts':30,'page_errors':errors,'mobile_overflow':False,'fallback':'passed','persistence':'passed'}, ensure_ascii=False))
    assert not errors
    browser.close()

