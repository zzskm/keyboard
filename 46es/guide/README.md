# 46es 설계 검토·조립 가이드 생성기

`guide_v5.json`(내용, 기본값)과 CAD 모델에서 정적 웹페이지 한 장(`index.html` + `img/`)을 만든다. 게시본은 <https://zzskm.github.io/keyboard-46es/>(v5, 현행 설계)이고, 이전 판 v4는 <https://zzskm.github.io/keyboard-46es/v4/>에 기록용으로 둔다(서로 lede에서 링크).

`guide_v4.json`은 v4 출력 부품과 부분 실측 케이스·MX 스위치·OEM 키캡을 포함한 검토 모델(`model/46es_assembly_review.sc`)을 사용한다(`--spec guide_v4.json`). 원본은 `model/46es_mount_seam_v4.sc`다. [참고 형상 치수 근거·재생성 방법](../docs/assembly-reference-2026-11-06.md)에 측정값과 가정을 구분했다. `guide_v3.json`은 v3 판 기록으로 남겨 두었다(`--spec guide_v3.json`).

**v5(2026-11-06, 현행 설계·기본값)**: `guide_v5.json` + `assembly_v5.json`은 v5 검토 모델(`model/46es_assembly_review_v5.sc`, 원본 `model/46es_mount_seam_v5.sc`)을 쓴다. 두 단 커버(바닥 테두리 +2.4 / 창 둘레 턱 Z 19 = +5.0; 3차 안전마진으로 포켓 위 살 1.3), 아래 다리 자석 2쌍, 키캡 여유 1 mm, upper plate 1.7, 참고 키캡 착좌 + 6.0이 들어 있다. 기본 출력은 `out/`이고 게시는 `keyboard-46es/` 루트다. 사용자 결정(2026-11-06): 주문 전이므로 v5가 현행 설계이고 v4는 `v4/` 아래 기록용. [v5 문서](../docs/v5-cover-magnet-margin-2026-11-06.md)를 본다.

```powershell
python build_guide.py                                   # v5 → out/
python build_guide.py --spec guide_v4.json --out out_v4   # v4 기록판
```

조립 화면의 머리글과 케이스 높이 안내는 `assembly_v*.json`의 `labels`(`eyebrow`, `case_hint`)에서 읽는다. 없으면 v4 문구를 쓴다. 검토 모델 매니페스트에 `generator`가 있으면 그 생성기의 해시를 확인한다. `check_browser.py`는 `GUIDE_URL`, `GUIDE_SHOT_PREFIX`, `GUIDE_SECOND_STEP_TITLE` 환경 변수로 다른 판을 확인할 수 있다(Python playwright 필요).

## 무엇이 자동이고 무엇을 손으로 쓰나

| 자동(모델·CSV에서) | 손으로(`guide_v4.json`) |
|---|---|
| 렌더 PNG. 단계마다 보일 바디, 카메라, 단면을 spec에 적으면 `solidcraft-cli snapshot`으로 찍는다 | 조립 단계 문장, 확인할 것, 안 맞을 때 대처 |
| 출력 부품 표의 부피와 X×Y×Z(`solidcraft-cli eval`), JLC 최소 크기 경고 | 맞춤 검토 표, 열린 항목, 구매품, 국부 시험, 결정 기록 |
| 상단 칩의 실측 개수와 모델 바디·오류 수, 실측 카드(`model/measurements.csv`) | 실측 카드의 짧은 이름과 표시 문구(`names`, `pills`) |
| 문장 속 숫자 토큰: `{{p:매개변수}}`, `{{v:바디}}`(cm³), `{{d:바디}}`(크기), `{{n:패턴}}`(바디 수) | |
| 푸터의 모델 이름·SHA-256·피처·스케치·오류 수와 생성일 | |

모델이 바뀌면 다시 돌리기만 하면 렌더, 부품 표, 토큰 숫자가 따라온다. 바디 이름이 바뀌어 spec의 패턴이 아무 바디도 못 찾으면 빌드가 멈추고 그 패턴을 알려 준다.

## 실행

### 3D 단계별 조립

v4는 기존 이미지 가이드 앞에 Three.js 조립 화면을 함께 생성한다. 15단계 이동,
추천·위·아래 시점, 회전·확대·이동, 분해 보기, 부품 선택 강조, 현재 단계/전체 부품
목록과 검색, 부품 준비 체크를 제공한다. 단계 완료는 기존 체크박스와 동일한 기록을
사용하며, 마지막 단계와 준비 체크는 별도 브라우저 저장소에 보관한다.

`assembly_v4.json`은 단계별로 보여 줄 부품(`show`), 강조 부품(`focus`), 작업에 필요한
수량(`needs`), 추천 시점(`view`), 설명 보충(`note`), M2 체결 위치(`hardwareStages`)를
정한다. 작업대 위의 커버·plate 모듈은 케이스와 따로 표시하고, 임시 장착 후 들어내는
순서도 명시한다. 설명·부품 규격과 전체 수량은 `guide_v4.json`을 그대로 사용한다.
새 구매품에는 안정적인 `id`를 부여하고 `hardware_bodies`에 CAD 바디를 연결한다.
형상이 없는 구매품은 목록과 설명만 제공한다. 준비 체크는 확보 여부이며 재고 차감은 아니다.

`assembly.py`는 CAD 조립 좌표 그대로 부품별 binary STL을 내보내고 CAD 경계 상자와
정점 좌표를 대조한다. 인쇄 방향으로 회전된 주문용 STL은 사용하지 않는다.
모델 해시와 부품 매핑을 키로 `guide/.cache/web/`에 캐시한다. M2 나사와 너트는
위치별로 분리하여 아직 장착하지 않은 브래킷·게이트 체결물이 보이지 않게 한다.
하우징·하드웨어 등 참고 형상에는 별도 안내를 붙인다. OEM 키캡은 마지막 장착 단계에서 표시한다. 스위치는 하우징·스템·접점의 색을 구분한다. 배선은 3D 형상이 없다. `앞 높이` 시점에서 케이스 테두리와 커버의 높이 차이를 확인할 수 있다.

Three.js 0.180.0, OrbitControls, STLLoader와 MIT 라이선스는 `assets/vendor/`에
고정하여 포함한다. 빌드 시 npm 또는 CDN 접속이 필요 없다. 배포할 때는 `index.html`,
`img/`뿐 아니라 출력 폴더 전체(`models/`, `vendor/`, `assembly.json`, JS/CSS)를 복사한다.
`--skip-renders`도 새 모델의 웹 메시가 없으면 생성한다. 원본 CAD·실측 자료·생성기와 검토 CAD의 해시를 검사하므로 원본을 수정하면 먼저 `python tools/build_assembly_reference.py`로 검토 모델을 갱신한다.

로컬 확인은 파일을 직접 여는 대신 HTTP 서버를 사용한다.

```powershell
python guide/build_guide.py --skip-renders
python -m http.server 8766 --bind 127.0.0.1 --directory guide/out
# http://127.0.0.1:8766/#interactive
```

WebGL 또는 모델 로딩 실패 시 단계별 참고 이미지를 펼치며 설명·목록·체크는 계속
사용할 수 있다. JavaScript가 꺼져 있어도 기존 전체 이미지·조립 설명은 남는다.

브라우저 회귀 검증은 Playwright가 설치된 Python 환경에서 위 서버를 실행한 뒤
저장소 루트에서 `python guide/check_browser.py`로 실행한다. 기본 Chrome 경로가
다르면 `BROWSER_EXECUTABLE` 환경 변수에 실행 파일을 지정한다. 15단계 이동,
분해 조작, 선택·검색, 완료·준비 기록 복원, 모바일 가로 넘침, 3D 모듈 로딩 실패를
검증한다. 스크린샷은 무시되는 `guide/.cache/`에 저장한다.

참고: [BRICK SORT3R의 부품 준비·조립 흐름](https://robotsquare.com/books/ev3discovery/tutorial-brick-sort3r/index.html),
[buildinginstructions.js의 단계별 3D 지침](https://github.com/LasseD/buildinginstructions.js/).
LDraw 전용 라이브러리를 이식하는 대신 기존 CAD 바디를 직접 Three.js로 표시한다.

SolidCraft가 설치돼 있어야 한다(`C:\Program Files\SolidCraft\solidcraft-cli.exe`, 다르면 `--cli`).

```
cd 46es/guide
python build_guide.py                         # → out/index.html, out/img/
python build_guide.py --only hero,st-ctrl     # 이 렌더만 다시, 나머지는 캐시
python build_guide.py --skip-renders          # 문장만 고쳤을 때(캐시 없으면 실패)
python build_guide.py --out D:/work/zzskm.github.io/keyboard-46es --clean-img   # 게시 폴더로
```

- 렌더 한 장은 모델을 열어 약 27초 걸린다. 기본 4장씩 병렬(`--jobs`)이라 전체 13장이 약 4분이다.
- 결과는 `.cache/`에 모델 해시와 렌더 설정 키로 저장된다. 문장만 바꾸면 몇 초, 모델이 바뀌면 전부 다시 찍는다. `.cache/`와 `out/`은 git에 넣지 않는다.
- `--clean-img`는 출력 폴더의 `img/`에서 이번 빌드가 쓰지 않는 PNG를 지운다.

## 게시

```
cd D:/work/zzskm.github.io && git pull --ff-only
python D:/work/keyboard/46es/guide/build_guide.py --out D:/work/zzskm.github.io/keyboard-46es --clean-img                          # v5(기본) → 루트
python D:/work/keyboard/46es/guide/build_guide.py --spec guide_v4.json --out D:/work/zzskm.github.io/keyboard-46es/v4 --clean-img   # v4 기록판
git add keyboard-46es && git commit -m "docs(keyboard-46es): 가이드 재생성" && git pull --rebase && git push
```

Pages 저장소에는 자동 커밋이 계속 쌓이므로 커밋 전에 `pull --ff-only`, push 전에 `pull --rebase`를 한다.

## spec 구조 (`guide_v5.json` · `guide_v4.json` 공통)

- `model`, `measurements`: spec 기준 상대 경로.
- `cameras`: `{target, yaw, pitch, distance, fov}`(mm, 라디안). yaw 0은 −Y(앞)에서, **yaw −π/2는 +X 쪽에서** 본다. pitch +π/2는 위에서 본 평면도.
- `groups`: 바디 이름 패턴(`*` 와일드카드) 묶음. 다른 묶음은 `@이름`으로 참조한다.
- `renders`: `{id, show, hide?, camera?, size?, section?, style?}`.
  - `section`은 CLI `--section` 값이다. `x=6.494`는 작은 쪽을 남기고, `,flip`을 붙이면 큰 쪽을 남긴다.
  - `style`은 `{body, opacity, color}`로 반투명·색을 지정한다.
- `page`: 제목, 칩(`{"auto":"measurements"}`, `{"auto":"model"}` 또는 `{tone, text}`), 범례, 대표 렌더.
- `sections`: 순서대로 쓰인다. `type`은 `summary`, `structure`, `fit`, `issues`, `parts`, `assembly`, `steps`, `table`, `measurements`, `log` 중 하나다. 체크박스 id는 `issues[].id`와 `assembly…steps[].id`에서 오므로, 바꾸면 보는 사람의 체크 기록이 끊긴다.

문장 필드에는 HTML을 쓸 수 있다(`<b>`, `<code>`, `<small>`). spec은 저장소 작성자만 고치는 신뢰 입력이다.
