# v5 3D 테크니컬 모션 조립 가이드

`guide_v5.json`(정적 참고 표·fallback hero 렌더) + `assembly_v5.json`(6단계·9레이어·36초 모션 스키마) + `model/46es_assembly_review_v5.sc` → CAD 추적형 인터랙티브 3D 조립 시퀀서. 게시: https://zzskm.github.io/keyboard-46es/ (`/v4/`는 과거 기록, 현행 생성 대상 아님).

모든 외곽 치수(`W × D × H mm`), 경사각(`°`), 부품/접점 수량(`197 pcs`), 출력 부피(`cm³`), 16칸 BOM 합계, 6칸 CAD 리포트 수치는 하드코딩 없이 CAD SSOT(`assembly.json` + 해시 검증된 `assembly-reference-v5-verification.json`)와 Three.js 씬 객체에서 단일 계산(`computeMetrics()`)한다.

## 아키텍처

- **6개 조립 단계 (`assembly_v5.json` `schema_version: 2`, 총 197 pcs)**:
  - `G1-BASE`: PSD60 하우징, MJF mount 4, 뒤 받침 블록 3, M3 열압입 인서트 6, 케이스 나사 6 (20 pcs)
  - `G2-CORE`: 컨트롤러 브래킷 1, Pro Micro 1, USB 아웃렛 1, 브래킷 M2×6/너트 각 2, 절차적 1N4148 다이오드 46 + 비집계 매트릭스 배선 16경로 (53 pcs)
  - `G3-PLATE`: 분할 plate L/R 2, spine 1, 앞 이음 M2×5 1, spine M2×6 4, plate/spine M2 너트 5, 상부 M3×10 볼트 6 (19 pcs)
  - `G4-SW`: MX 스위치 46개 (역회전 OBB로 개별 분리, 92 금속 접점 핀) (46 pcs)
  - `G5-COVER`: 투명 SLA 레진 커버 L/T/R 3, Ø3×2 네오디뮴 자석 10 (13 pcs)
  - `G6-KEYCAP`: OEM 키캡 46개 (`1u` 43 · `1.25u` 1 · `2u` 1 · `2.25u` 1 개별 분리) (46 pcs)
- **9개 시맨틱 가시성 레이어 (`ALL` / 토글 / Shift·더블클릭 `SOLO`, 총 197 pcs)**:
  - `CASE(1, 단축키 C)` · `MNT(7)` · `WIRE(49)` · `PLT(3)` · `SW(46)` · `CVR(3)` · `CAP(46)` · `BOLT(32)` · `MAG(10)`
- **36.0초 비중첩 결정론적 시퀀스 (`assets/motion/`)**:
  - `0.00–2.00s`: 주황 3D 바운딩 박스 선 드로잉 + 실측 치수/경사각 카운트업(`1.75s` 완료)
  - `2.00–4.05s`: 6레이어 로컬 Z 분해 + 42개 체결부 로컬 삽입 축 사전 부유
  - `4.05–10.40s`: `STEP 1→6` 순차 안착 및 로컬 축 볼트/너트/인서트/자석 체결(점선 축선·0.28 mm 가이드 실린더·블루 착좌 링, `G3-PLATE` 히어로 `M3×10` 구간 `2.25s`)
  - `10.40–11.00s`: `0.60s` 완조립 정지 홀드
  - `11.00–16.00s`: X-Ray 와이어프레임 + 수직 스캔 평면(150 CAD 검사점: 체결부 42 · 스위치 핀 92 · Pro Micro 패드 16, 단일 판정 함수 `evaluateScanTarget()` 동기화)
  - `16.00–20.00s`: 코어(`G2/G3/G4`) 100% 컬러 · 외곽(`G1/G5/G6`) 20% 고스트 + 회전 대응 동적 4사분면 SVG 지시선
  - `20.00–26.00s`: Key #40(`2.00U`) 안착 시뮬레이션(`SIM ΔZ +1.8 mm` → `SIM SEAT 0.0 mm ✓`, 실측 `COV CLR 1.02 mm` 병기)
  - `26.00–32.00s`: 키보드 우측 이동 + 16칸 인터랙티브 BOM 그리드(고유 CAD 바디 ID 썸네일, 호버/클릭 3D 하이라이트, 숨김 레이어 고스트 프리뷰)
  - `32.00–36.00s`: 6그룹 요약 범례 + 100% 런타임 실측 6칸 CAD 리포트(`ENVELOPE`, `3D PRINT cm³`, `FASTENERS`, `KEYS · LAYOUT`, `MATRIX · WIRE`, `CAD FIT 0 OVL ✓`)
- **2-모드 카메라 & 2단 슬림 콘솔**:
  - 자유 360° 오빗(드래그)·팬(우클릭/Shift)·캔버스 휠 줌(`0.55×~4.5×`)·프리셋 5종(`ISO/TOP/FRT/SID/BTM`)·턴테이블(`⟳`)·수동 분해(`EXP`, `E`)·수동 X-Ray(`XRAY`, `X`)·초기화(`↺`, `R`).
  - `BTM` 하부 시점에서 바닥면 완전 차단 및 하부 보강 조명 자동 점등. 재생(`▶`/`Space`) 시 직전 타임코드 복귀 + `450ms` 인터럽트 가능 카메라 블렌드.
  - 3D 부품/볼트/키 호버 시 하단 1줄 CAD 추적 칩(`#hud-pick`) 표시.
  - `SPEC ↓` 버튼으로 하단 `<details id="reference-docs">` 출력·구매·시험 표 및 `diagrams.py` SVG 7종으로 즉시 이동.
  - WebGL 불가/실패 시 `img/hero.png` 정적 fallback과 `<details>` 자동 오픈으로 전환.
- **런타임 자산**: `assets/vendor/` = Three.js 0.180.0 (`three.module.js`, `three.core.js`, `GLTFLoader.js`, `BufferGeometryUtils.js`, `LICENSE`, 오프라인, `OrbitControls` 미사용). `models/assembly.glb`는 `glb.py`로 양자화 압축(`KHR_mesh_quantization`, 주문 1 시험편 `CTRL_SNAP_TRIAL`·`SEAM_COUPON_L` 제외).

## 실행 (저장소 루트)

SolidCraft CLI + Python NumPy·Shapely·ezdxf 필요(`SOLIDCRAFT_CLI` 또는 기본 `C:/Program Files/SolidCraft/solidcraft-cli.exe`, `--cli` 변경).

```sh
python 46es/guide/build_guide.py --clean-img
python -m http.server 8766 --bind 127.0.0.1 --directory 46es/guide/out
```

`http://127.0.0.1:8766/`. 원본 CAD/측정 JSON/생성기/검토 CAD 해시 불일치 시 중단. `.cache/`, `out/`, `out_*/`는 생성물(Git 제외).

## 게시

```sh
python 46es/guide/publish_guide.py            # origin/main에 있는 깨끗한 커밋에서
python 46es/guide/publish_guide.py --dry-run  # 빌드·브라우저 검사만
```

빌드(`out_publish/`) → 브라우저 검사(`check_browser.py`) → Pages clone(`D:/work/zzskm.github.io/keyboard-46es`, `v4/` 유지) 복사 → 커밋·push → 라이브 `build.json`·`index.html` 대조까지 일괄 수행한다.

## 시각 검토

```sh
python -B 46es/tools/check_repository.py
python 46es/guide/check_browser.py --site 46es/guide/out
python -B 46es/guide/review_guide.py --steps step1 step2 step3 step4 step5 step6 --views motion
```

- `review_guide.py`는 `--assembly-only`로 로컬 빌드 후 Playwright(1920×1080)로 36초 핵심 시점 11장 + `CASE OFF + BTM` 1장 + `STEP 1~6` 6장을 `guide/.cache/visual-review/`에 캡처하고 `review.json`을 기록한다(`pipeline.py --status`의 `review` 단계가 이 해시로 판정).
- `check_browser.py`는 6개 해상도(`1920×1080`, `1440×1100`, `1280×800`, `1024×768`, `768×1024`, `390×844`)에서 SSOT 불변식, 9레이어 토글·SOLO, 2-모드 카메라·하부 시점, 36초 전 구간(히어로 볼트 `7.6s`·홀드 `10.7s` 포함), 인터랙티브 BOM, 실측 6칸 CAD 리포트, `STEP 1~6`, `<details>` SVG 로드, WebGL 실패 fallback을 자동 검증한다.
- SolidCraft 없는 UI 검토: `python 46es/guide/preview_from_published.py --published <v5 자산 폴더>`.
- 폐지된 구 16단계 조립서 및 `r2` 비교 UI/모델(`comparison_r2.json`, `model/reference_r2/`, `tools/build_r2_reference.py`)은 Git 이력에서 조회할 수 있다.
