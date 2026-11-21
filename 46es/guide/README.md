# v5 3D 테크니컬 모션 조립 가이드

`guide_v5.json`(정적 참고 표·fallback hero 렌더) + `assembly_v5.json`(5그룹·32초 모션 스키마) + `model/46es_assembly_review_v5.sc` → 풀스크린 1920×1080 테크니컬 모션 3D 웹 가이드. 게시: https://zzskm.github.io/keyboard-46es/ (`/v4/`는 과거 기록, 현행 생성 대상 아님).

모든 외곽 치수(`W × D × H mm`), 경사각(`°`), 부품/접점 수량(`pcs`), 16칸 BOM 합계, 6칸 빌드 리포트 수치는 하드코딩 없이 Three.js가 실제 씬에 생성한 객체 트리에서 실시간 계산한다.

## 아키텍처

- **5개 조립 그룹 (`assembly_v5.json` `schema_version: 2`)**:
  - `G1-BASE`: PSD60 하우징, MJF mount 4, 뒤 받침 블록 3, M3 인서트 6, 케이스 나사 6 (20 pcs)
  - `G2-CORE`: 컨트롤러 브래킷 1, Pro Micro 1, USB 아웃렛 1, 브래킷 M2×6/너트 각 2, 절차적 1N4148 다이오드 46 + 4×12 매트릭스 배선 16경로 (53 pcs)
  - `G3-PLATE`: 분할 plate L/R 2, spine 1, 앞 이음 M2×5 1, spine M2×6 4, plate/spine M2 너트 5, 상부 M3×10 볼트 6 (19 pcs)
  - `G4-SW`: MX 스위치 46개 (역회전 OBB로 개별 분리, 92 금속 접점 핀) (46 pcs)
  - `G5-TOP`: 투명 레진 커버 L/T/R 3, Ø3×2 자석 10, OEM 키캡 46개 (`1u` 43 · `1.25u` 1 · `2u` 1 · `2.25u` 1 개별 분리) (59 pcs)
- **32.0초 결정론적 시퀀스 (`assets/motion/`)**:
  - `0–7s`: 주황 3D 바운딩 박스 선 드로잉 + 실측 치수/바닥 실측 경사각(`2.2°`) 카운트업 → 5레이어 로컬 Z 분해 후 `G1→G5` 안착
  - `7–13s`: X-Ray 와이어프레임 전환 + 수직 스캔 평면 상승하며 체결부 42 · 스위치 핀 92 · Pro Micro 패드 16 주황→파랑 하이라이트
  - `13–17s`: 코어(`G2/G3/G4`) 100% 컬러 · 외곽(`G1/G5`) 20% 고스트 + SVG 지시선 4종
  - `17–23s`: Key #40(`2u` 썸키) 클로즈업 줌인 → `+1.8 mm` 들뜸 주황 점멸(`⚠`) → 수직 결착 파랑(`0 ✓`) → 원위치 복귀
  - `23–29s`: 키보드 우측 이동/축소 + 좌측 4×4(16칸) 오프스크린 3D 아이소메트릭 BOM 그리드 스태거 등장
  - `29–32s`: 전체 아이소메트릭 복귀 + 하단 6칸 빌드 리포트 카운트업
- **인터랙티브 컨트롤 & 참고 자료**:
  - 로드 시 `0.0s` 완성 상태로 정지 대기 → `[▶/⏸]`(`Space`), `0.0s–32.0s` 스크러버(`←/→`), `[STEP 1~5]`(`1~5`, 고정 아이소메트릭 누적 탐색)
  - 하단 접이식 `<details id="reference-docs">`에 출력 부품·구매품·주문 1 시험 표와 `diagrams.py` SVG 7종(배선 지도, 핀맵, 다이오드, 자석 극성, 스냅, 46키 시험표, 키캡 배열) 보존.
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
python -B 46es/guide/review_guide.py --steps step1 step2 step3 step4 step5 --views motion
```

- `review_guide.py`는 `--assembly-only`로 로컬 빌드 후 Playwright(1920×1080)로 32초 핵심 시점 9장 + `STEP 1~5` 5장을 `guide/.cache/visual-review/`에 캡처하고 `review.json`을 기록한다(`pipeline.py --status`의 `review` 단계가 이 해시로 판정).
- `check_browser.py`는 1920×1080·1440×1100·390×844에서 초기 정지 상태, `window.__motionMetrics` 실측/카운팅 어서션, 32초 6개 구간, 16칸 BOM 썸네일, `STEP 1~5`, `<details>` SVG 로드, WebGL 실패 fallback을 자동 검증한다.
- SolidCraft 없는 UI 검토: `python 46es/guide/preview_from_published.py --published <v5 자산 폴더>`.
- 폐지된 구 16단계 조립서 및 `r2` 비교 UI/모델(`comparison_r2.json`, `model/reference_r2/`, `tools/build_r2_reference.py`)은 Git 이력에서 조회할 수 있다.
