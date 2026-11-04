# 46es 3D 프린팅 케이스 — 제작 모델 준비 (실측 대기)

> **제작용 아님.** 여기의 값은 대부분 자리표시이거나 미검증 참고값이다. 바디는 PSD60 자리에 둔 **하우징 대용 바디 1개**(Wilmore STL 기반, 간섭 확인용)뿐이고, 46es 부품(프레임·plate·커버) 솔리드와 STL은 만들지 않았다. 해당 부품의 실측(`measurements.csv`)이 끝나기 전에는 출력 파일을 만들지 않는다.

현재 상태 (2026-11-04): DWG 검사 완료, The_Wilmore.stl에서 하우징 대용값 추출 → 매개변수 107개, 스케치 7개, 바디 1개(`REF_HOUSING_WILMORE_NOT_PSD60`). **다음 작업은 PSD60 실측이다.** 실측값이 나오면 하우징 대용 바디와 초안 스케치가 함께 따라간다. 근거는 `../inspection/46es_r2_dwg_inspection.md`(DWG), `../inspection/wilmore/README.md`(Wilmore)에 있다.

| 파일 | 내용 |
|---|---|
| `parameters.csv` | 치수 입력용 매개변수 107개. `TBD_` = 미확정, `CAND_` = GH60 후보 좌표(추정), `REF_` = DWG r2 참고값, `REF_WIL_` = Wilmore STL 추정값(PSD60 아님). 주석에 근거와 측정 ID를 적었다. SolidCraft `parameters.import` 형식이다. |
| `measurements.csv` | 실측 시트 M01–M21. 측정값 칸은 비어 있다. `현재 후보값`에 Wilmore 값을 함께 적었다. |
| `46es_draft_sketches.sc` | SolidCraft 디자인. 매개변수, 2D 초안 스케치 5개, 하우징 대용 바디(스케치 2개 + 피처 4개). 스케치는 모두 자유도 0. |
| `46es_draft_sketches_top.png` | 위에서 본 초안(2026-11-03, 하우징 대용 바디 추가 전) |
| `46es_housing_ref_wilmore_iso.png` | 하우징 대용 바디와 초안 스케치 |
| `samples/` | B 단계 스위치 홀 시험 쿠폰(`46es_sw_hole_sample.sc`, 홀 13.7–14.3 × 행 A 노치/행 B 개방 포켓, M2 구멍). 시험물이며 부품이 아니다. STL/STEP 내보냄, 미발주 |

좌표계: 원점 = GH60 PCB 기준점(앞·왼쪽), X 오른쪽, Y 뒤쪽, Z = 0은 케이스 지지대 상면(미확정)이다. 하우징의 타이핑 경사(Wilmore 4.63°, PSD60 문서값 6°)는 뺀 PCB면 기준 좌표다.

| 스케치 | 평면 높이 | 내용 |
|---|---|---|
| `SK00_CASE_ENVELOPE_TBD` | 0 | PSD60 내측 외곽(지금은 Wilmore 대용값), GH60 PCB 보조선, 컨트롤러·USB 점유 영역(컨트롤러는 근거 없는 자리표시) |
| `SK10_FRAME_DRAFT_TBD` | 0 | 하부 프레임 외곽(모따기), 리브 경계 보조선, 케이스 체결 후보 6, 스탠드오프 후보 6 |
| `SK20_PLATE_DRAFT_TBD` | `TBD_frame_T + TBD_standoff_H` | plate 외곽(모따기), 스탠드오프 구멍 6, 케이스 지지대 간섭 확인 원(보조선), 스위치 홀 템플릿 2개(`TBD_sw_hole`, 간격 `TBD_sw_pitch`) |
| `SK21_REF_r2_P2_DWG_NOT_FOR_PRODUCTION` | 위와 같음 | DWG r2 스위치 판 형상(보조선, 고정). 키 위치·각도 참고용 |
| `SK30_COVER_DRAFT_TBD` | `… + TBD_plate_T` | 커버 외곽(R `TBD_cover_R`), 벽 두께 보조선 |
| `SK40_HOUSING_PROFILE_REF_WILMORE` | YZ, X = −`REF_WIL_out_xL` | 하우징 측면 단면(외형 표시용) |
| `SK41_HOUSING_POSTS_CAND` | −`TBD_support_H`(바닥) | 하우징 기둥 6개(GH60 `CAND_` 좌표, Ø`TBD_case_post_D`, 구멍 Ø`TBD_case_screw_D`) |

### 하우징 대용 바디 `REF_HOUSING_WILMORE_NOT_PSD60`

PSD60을 실측하기 전에 부품 간섭을 3D로 보기 위한 자리표시 바디다. **출력하지 않는다.**

| 피처 | 무엇을 따르나 |
|---|---|
| `HOUSING_OUTER_REF_WIL` | 외형: `REF_WIL_out_*`·`bot_*`·`chamfer_*`(Wilmore 고정값), 테두리 높이 `TBD_support_to_rim_F/B` |
| `HOUSING_CAVITY_TBD` | 내부 공간: SK00 내측 외곽(`TBD_case_in_W/D/R`, `TBD_pcb0_dx/dy`), 바닥 깊이 `TBD_support_H` |
| `HOUSING_POSTS_CAND` | 기둥: `CAND_H01_X` … `CAND_H06_Y`, `TBD_case_post_D`, `TBD_case_screw_D` |
| `HOUSING_USB_CUT_TBD` | USB 개구부: `TBD_usb_X/W/H/Z` |

부피 297,430.3 mm³(계산값과 같음). Wilmore 메시와 단면을 비교하면 내벽은 0.01, 외곽은 0.15 이내다. 기둥 좌표는 Wilmore가 아니라 GH60 후보값이다(Wilmore와 최대 0.52 차이, 비교표는 `../inspection/wilmore/README.md`).

하우징 관련 `TBD_` 매개변수 13개는 지금 식이 `REF_WIL_…`이다(`TBD_case_in_W = REF_WIL_in_W` 등). 실측하면 그 `TBD_` 식만 실측값으로 바꾼다. `REF_WIL_`는 비교용으로 남긴다.

---

## 실측 후 재개 절차

### 1. 측정값 기록

`measurements.csv`의 `실측값`·`측정일`·`메모` 칸을 채운다. 여러 곳을 잰 항목은 모든 값을 남긴다(예: `286.62 / 286.58 / 286.71`). 사진·본뜨기 파일은 `measurements/` 폴더에 측정 ID로 시작하는 이름으로 둔다(예: `M03_corner_FL.jpg`).

### 2. 매개변수 반영

`parameters.csv`에서 해당 행을 고친다.

- 값: `expression`을 실측에서 정한 설계값으로 바꾼다. 여러 값을 쟀다면 어느 값을 썼는지 주석에 적는다(최솟값, 평균 등).
- 주석: 상태 태그를 `[실측 YYYY-MM-DD Mxx]`로 바꾼다.
- 이름: 근거가 확정된 값은 `TBD_`·`CAND_`를 뗀다(예: `TBD_case_in_W` → `case_in_W`, `CAND_H01_X` → `H01_X`). 접두어가 남아 있으면 아직 미확정이라는 뜻이다.
- Wilmore 대용: 지금 `REF_WIL_…`을 참조하는 `TBD_` 행도 같은 방법으로 식을 실측값(숫자)으로 바꾼다(예: `TBD_case_in_W`의 `REF_WIL_in_W` → `286.52 mm`). `REF_WIL_` 행은 고치지 않는다.

남은 미확정 개수는 `grep -c '^TBD_\|^CAND_' parameters.csv`로 확인한다.

### 3. SolidCraft 갱신

1. `46es_draft_sketches.sc`를 SolidCraft에서 연다. MCP로 열 때는 서버가 허용한 폴더만 읽을 수 있다. 서버에 `--allow-path D:\work\keyboard\46es\model`을 추가하거나, 파일을 SolidCraft recovery·temp 폴더로 복사해 연다.
2. 바뀐 값은 `parameters.change`로 반영한다. 이름을 바꿀 때는 `new_name`을 쓰면 스케치 참조가 따라간다. 여러 개를 바꿀 때는 `batch` + `coalesce_parameters: true`를 쓴다.
3. 확인: 스케치 7개 모두 `dof 0`, 타임라인 오류 0. 외곽은 `sketch.export_dxf`로 내보내 기대 좌표와 비교한다(검사 때 쓴 방식). 하우징 대용 바디는 부피와 `body_topology {"faces":"cylinders"}`의 기둥 중심으로 확인한다.
4. 저장한 뒤 `parameters.csv`와 `.sc`의 값이 같은지 대조하고 함께 커밋한다.

### 4. 다음 단계로 넘어가는 조건

**표의 실측이 끝나고 그 부품에 쓰이는 `TBD_`·`CAND_` 매개변수가 하나도 남지 않았을 때만** 부품 솔리드·STL을 만든다. Wilmore 대용값(`REF_WIL_`)을 참조하는 `TBD_`도 미확정으로 센다. 하우징 대용 바디는 어느 단계에서도 출력하지 않는다.

| 단계 | 필요한 실측 | 만들 것 |
|---|---|---|
| A. 체결 시험 프레임 | M01, M02, M03, M07, M08, M09, M10 (+M18 공정) | 얇은 판(2–3 mm) 시험 출력. 6개 나사가 억지 없이 들어가는지 확인 (planning.md §4) |
| B. 스위치 홀 샘플 | M11, M19, M18 | 13.7 – 14.3 홀(0.1 간격) + 걸쇠 노치/개방 포켓 두 행 + M2 구멍 쿠폰 → `samples/`. 입력은 2026-11-04 사용자 결정으로 채움(M11 DWG값 채택, M18 FDM·JLCPCB 후보, M19 Gateron Milky Yellow). 출력 전 확인 필요 |
| C. 코너 R 샘플 | M03, M06, M18 | 커버 코너 R2 / 2.5 / 3 / 3.5 샘플 (실제 벽 두께·결합 턱 포함) |
| D. 하부 프레임 | A 결과 + M05, M13, M14, M15, M16 | 하부 프레임 솔리드 |
| E. 스위치 plate | B 결과 + M12, M20, M21 | plate 솔리드 (배치는 현물 대조 후 SK21 참고) |
| F. 커버 | C 결과 + M17 | 커버 솔리드 |
| G. 전체 출력 | A–F 시험 결과를 CAD에 반영한 뒤 | 출력 업체용 STL/STEP |

시험 결과(억지 조립, 간섭, 끼움)는 `measurements.csv`의 메모나 `../inspection/`에 기록한 뒤 CAD에 반영한다.

### 5. 재현용 명령

```bash
# DWG 요약 (읽기 전용, CADCraft)
"C:/Program Files/ArtCraft/CADCraft/cadcraft-cli.exe" info ../cad/46es_r2_keyboard.dwg
# 독립 교차 검증 / Z·두께 확인
python -I ../inspection/scripts/dwg_census.py ../cad/46es_r2_keyboard.dwg census.json
python -I ../inspection/scripts/dwg_thickness.py ../cad/46es_r2_keyboard.dwg census.json
```
