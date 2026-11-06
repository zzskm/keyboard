# v5 2차 작업 계획: 두 단 커버 · 참고 키캡 높이 · B 쿠폰 1.7 — 2026-11-06

**상태: 수행함(2026-11-06, 두 번째 세션). 결과 수치는 §12, 새로 걸린 함정은 §13에 있다.** 아래 §0–§11은 계획 원문이다(§3·§10의 "7곳 꼭대기 19.0" 표현은 §12-1에서 바로잡았다). 커밋·배포·발주는 하지 않았다.

금지: 커밋·배포·발주. v4(`46es_mount_seam_v4.sc`, sha `606d1bd9…`)와 v5 1차(평판 Z 18, sha `66a2ec87…`)는 보존한다. plate는 바꾸지 않는다([[feedback-46es-plate-is-master]]). 케이스(REF_PSD_*/REF_WIL_*)도 바꾸지 않는다.

---

## 0. 결정 사항 (판단 완료)

사용자가 남긴 질문은 "케이스 윗면 돌출은 최소로 하되 커버가 키캡 쪽에서는 더 올라오게" 하는 형상이었다. 현재 형상을 수치로 확인한 결과는 §1에 있다. 결정은 다음과 같다.

| # | 항목 | 결정 | 근거 |
|---|---|---|---|
| D1 | 커버 형상 | **두 단**: 낮은 바닥 + 창 둘레를 따라 올라가는 턱(collar). 경사(모따기) 안은 **폐기** | 앞·뒤 베젤이 1.16–1.42 mm인 곳이 4곳, 2.66–2.76인 곳이 3곳이다(§1). 경사는 폭이 필요한데 그 폭이 없다. 턱은 베젤이 좁은 곳에서 자동으로 베젤 전체를 차지하면 된다 |
| D2 | 바닥 윗면 Z | **16.1** = plate 윗면 13 + 자석 2 + 포켓 여유 0.1 + 살 1.0. 테두리 14 기준 **+2.1** | 아래 다리 자석 포켓 윗면이 Z 15.1이고 그 위 살을 1.0 이상 남겨야 한다(재료 규칙 벽 ≥ 1.0). 테두리가 아니라 자석 적층에서 유도한다. 15.5(+1.5)로 더 내리려면 다리 포켓 2곳 위에만 국부 받침을 세워야 한다 → 복잡해서 비추천 |
| D3 | 턱 윗면 Z | **19.0** = 키캡 밑면 추정 17.3 (착좌 11.3 + 6.0) + 덮음 1.7. 테두리 기준 **+5.0** | r2는 착좌 + 9 = 덮음 3.0, 현재 v5(Z 18)는 0.7. "좀 더 올라오게" → 1.7. 모두 매개변수라서 r2 실측(§11-1) 후 한 줄로 바꿀 수 있다. 대안: 18.5(덮음 1.2, 앞 +4.5), 18.0(덮음 0.7, 앞 돌출 지금과 같음) |
| D4 | 턱 폭 | **1.5** (키캡에서 1.0 간격 + 턱 1.5) | 레진 벽 ≥ 1.0 여유. 베젤 < 2.5인 곳은 턱이 바깥면까지 차서 전체 높이 19.0이 된다 |
| D5 | 참고 키캡 밑면 | **착좌 + 4.2 → 착좌 + 6.0** (Z 15.5 → 17.3) | r2: 2T upper plate 위에서 키캡을 끝까지 누르면 유격이 거의 없다(사용자) → 바닥에서 착좌 + 약 2, 쉴 때 + 약 6. 지금 참고 키캡은 1.8 낮아서 4 mm 눌림 검사가 plate를 뚫는 "제외 항목"이 되어 있다. 올리면 **눌림 ↔ plate 윗면 0.3 여유**라는 실제 검사가 된다(1.7 결정의 근거 수치) |
| D6 | B 쿠폰 행 C | **`SMP_upper` 2 → 1.7**, 같은 파일에서 수정하고 order1에 다시 내보낸다 | 주문 1은 아직 안 나갔고, 1.7은 사용자 확정이다. 쿠폰은 plate 적층을 그대로 재현해야 의미가 있다. 파일 이름은 `46es_v4_sw_hole_coupon` 유지(README에 주석) |
| D7 | v5 1차(평판 Z 18) 보존 | 스냅샷 폴더 `model/review_v5/flat_Z18/` + 빌드 옵션 `--flat` | [[feedback-46es-dont-discard-parallel-lines]] |
| D8 | plate 모듈 2.8 mm 내리기 | **안 함** | mount·스탠드오프·배선·컨트롤러 재설계. 배선 공간은 이미 빠듯 |
| D9 | 창 여유 | **1.0 유지** | 사용자 요구. 좁은 베젤의 원인이지만 줄이지 않는다(§11-3에서 실물로 확인) |

**사용자가 계획 승인 때 알고 있어야 할 한 가지(§1):** 앞·뒤 가장자리는 키캡이 케이스 내벽에서 1.2–2.8 mm밖에 안 떨어져 있어서, 그 구간에서는 커버 바깥면이 턱 높이(Z 19.0, 테두리 +5.0)로 선다. "돌출 최소화"는 좌·우 가장자리와 T 커버 중앙(폭 ≥ 22)에서만 실현된다. 앞 돌출이 r2(3.5)·현재(4.0)보다 커지는 것이 싫으면 D3을 18.5 또는 18.0으로 낮춘다. 두 값 모두 매개변수 한 줄이다.

---

## 1. 제약 수치 (이번 세션에서 확인)

`model/46es_mount_seam_v5.sc`의 창(SK35_COVER_KEY_MARGIN_V5_1…4 = 키캡 바닥 외곽 + 1.0)과 커버 외곽(X −0.393…285.388, Y −0.367…94.967, 코너 R 2.5)의 최소 거리.

| 변 | 베젤 최소 | 키 중심(X, Y) | 다음으로 좁은 곳 |
|---|---:|---|---|
| 앞 | **1.155** | (161.6, 14.4) | 1.42 (96.4, 15.1) · 2.76 (252.1, 13.3) · 5.84 |
| 뒤 | **1.385** | (76.5, 82.6) · (185.3, 82.6) | 2.66 (54.6, 81.8) · 2.66 (207.2, 81.8) |
| 왼쪽 | 4.875 | (15.0, 54.7) | 5.87 · 23 이상 |
| 오른쪽 | 3.839 | (270.7, 19.7) | 6.28 · 6.28 · 22 이상 |

- 현재 커버 최소 벽 1.098이 바로 이 자리다(`seam-v5-thin-wall.json`).
- 경사안: 바닥 16.1 → 윗면 19.0(상승 2.9)을 60–67°로 만들면 폭 1.5–1.7 + 창가 평탄 1.0 = 2.5–2.7이 필요 → 위 7곳에서 불가. 모따기(`solid.chamfer`)는 창을 뚫고 실패한다.
- 기존 포켓은 모두 바닥 아래다: 보스 자석 포켓 윗면 Z 13.6(6곳), 다리 자석 포켓 윗면 Z 15.1(2곳: (94.0, 2.5), (167.7, 2.5), Ø3.2, 창까지 1.17–1.18). 바닥 16.1이면 살 2.5 / 1.0.
- 커버 바깥 수직면: 립 Z 12–13 + 바닥 13–16.1, 턱이 닿는 곳은 19.0까지.
- 명령 지원 확인(이번 세션, `describe_command`/`list_commands`): `solid.extrude`에 `taper`, `operation: intersect`, `profiles: [{point}]` + `exact_regions`, `start_offset`이 있다. `solid.chamfer`(distance/distance2/angle), `solid.combine`(target, tools, cut, keep_tools), `solid.remove`, `solid.cone`도 있다.

---

## 2. 모델 변경 — `tools/build_seam_v5.py` → `model/46es_mount_seam_v5.sc`

### 2-1. 매개변수 (`new_param`, `TBD_cover_T` 앞에 삽입; 기존 `v5_cover_protrude`는 **삭제**)

| 이름 | 식 | 값 | 설명(코멘트에 적을 것) |
|---|---|---:|---|
| `v5_rim_ref_Z` | 14 (유지) | 14 | 테두리 상단(M05 대략값). 비교 기준으로만 |
| `v5_legmag_skin` | 1.0 | 1.0 | 다리 자석 포켓 위 최소 살(레진 벽 규칙) |
| `v5_cover_base_Z` | `v4_plate_top_Z + TBD_magnet_T + TBD_magnet_clr + v5_legmag_skin` | 16.1 | 커버 바닥 윗면. 테두리 + 2.1 |
| `v5_keycap_bottom_above_seat` | 6.0 | 6.0 | 쉴 때 키캡 스커트 밑면 − 스위치 착좌(r2 근거, §11-1 실측으로 확정) |
| `v5_keycap_bottom_rest_Z` | `v4_plate_top_Z - TBD_upper_plate_T + v5_keycap_bottom_above_seat` | 17.3 | |
| `v5_skirt_cover_H` | 1.7 | 1.7 | 턱이 키캡 옆면을 덮는 높이(쉴 때). r2 3.0, v5 1차 0.7 |
| `v5_cover_top_Z` | `v5_keycap_bottom_rest_Z + v5_skirt_cover_H` (식 교체) | 19.0 | 턱 윗면 |
| `v5_collar_W` | 1.5 | 1.5 | 창 가장자리에서 턱 바깥면까지 |
| `v5_cover_top_above_rim` | `v5_cover_top_Z - v5_rim_ref_Z` | 5.0 | 보고용 |
| `v5_cover_base_above_rim` | `v5_cover_base_Z - v5_rim_ref_Z` | 2.1 | 보고용 |
| `TBD_cover_T` | 식 유지 `v5_cover_top_Z - (…)` | **6.0** | 코멘트 숫자(18, 5) 갱신 |

매개변수 수 206 → 213. `TBD_upper_plate_T` 1.7, `v5_key_margin` 1.0, 다리 자석 값은 그대로.

### 2-2. 피처 (커버 피처 뒤에 추가; 모두 컷이라 순서는 다리 자석 피처 뒤여도 된다)

**방법 A(1순위): 한 스케치 + 영역 선택 컷**

1. `SK36_COVER_DROP_V5`: 평면 = XY 오프셋 `TBD_frame_T + TBD_standoff_H + TBD_plate_T + TBD_cover_T`(= 턱 윗면, 다른 SK35와 같은 식). 고정점 선분으로 다음을 그린다.
   - 큰 사각형 X −2…288, Y −2…97 (외곽보다 큼).
   - 키 46개의 **창 + 턱** 사각형: 폭 `18.05 + (w_u − 1)·19.05 + 2·(v5_key_margin + v5_collar_W)`, 깊이 `18.05 + 2·(…)`, 회전 포함(= `verify_seam_v5.py` 100행의 `rect()`에 m = 2.5). 서로 겹쳐도 그대로 둔다(한 스케치).
2. `COVER_DROP_V5`: extrude cut, `sketch` = 위, `profiles: [{point: [x, y]}, …]`, `exact_regions: true`, `direction: negative`, `start_offset: 0.5`, `distance: v5_cover_top_Z - v5_cover_base_Z + 0.5`(→ 정확히 Z 16.1에서 멈춤), `targets`: 커버 3개.
   - 선택점: 0.05 mm 래스터(numpy/scipy, 이전 세션 방식)로 "큰 사각형 ∩ (키 사각형 합집합의 바깥)"의 연결 성분을 라벨링하고, 성분마다 거리변환 최대점을 한 점씩 쓴다.
   - **규칙:** 커버 외곽과 만나는 바깥 성분은 모두 선택. 외곽과 안 만나는 **갇힌 성분(턱과 턱 사이 홈)은 내접 폭 ≥ 2.0(거리변환 최대 ≥ 1.0)일 때만** 선택한다. 좁은 홈은 전체 높이로 남겨 먼지 홈을 만들지 않는다. 선택하지 않은 성분 목록을 `build_v5.json`에 기록.
   - 기대 부피 = (선택 영역 ∩ 커버 평면 면적, 래스터) × 2.9. 컷 전후 부피 차와 1 % 이내로 맞아야 한다.
3. 기존 `COVER_KEY_MARGIN_V5_1…4`(창), `COVER_LEGMAG_*`, `COVER_LIP_RELIEF_*`는 그대로(깊이 식이 `TBD_cover_T`를 따라 6.0 + 1 + 0.5로 늘어난다).

프로브: 실제 빌드 전에 `guide/.cache/v5/` 아래 임시 사본으로 2번만 먼저 돌려 (a) 겹치는 사각형이 든 스케치에서 영역 선택이 되는지, (b) 커버 bbox max Z가 19.0으로 유지되고 선택 영역 윗면이 16.1인지(아래 §3 BRep 검사) 본다.

**방법 B(A가 실패할 때): 도구 바디 + combine**
1. 키 사각형을 `margin_groups()`(m = 2.5)로 겹치지 않게 나눠 그룹별 스케치 → 첫 그룹은 new_body `V5_COLLAR_TOOL`, 나머지는 join. Z `v5_cover_base_Z` → `v5_cover_top_Z + 1`.
2. `V5_DROP_TOOL`: box X −2…288, Y −2…97, Z `v5_cover_base_Z` → `v5_cover_top_Z + 1` (new_body).
3. `solid.combine` target `V5_DROP_TOOL`, tools `[V5_COLLAR_TOOL]`, cut, keep_tools false.
4. `solid.combine` target 커버 L / T / R 각각, tools `[V5_DROP_TOOL]`, cut, keep_tools true (3개). 커버끼리 합쳐지지 않는다.
5. `solid.remove` `V5_DROP_TOOL`.
   - combine/remove의 document.json 스키마는 `solidcraft-cli run`으로 빈 문서에 한 번 실행해 저장한 뒤 읽어서 확인한다(이번 세션에서 안 봤다).
   - 방법 B는 갇힌 좁은 홈을 거를 수 없다 → 홈 폭 < 2.0인 곳이 있으면 해당 키 쌍만 턱 폭을 키워(국부 m) 메운다.

### 2-3. `--flat` 옵션
`python tools/build_seam_v5.py --flat` → DROP 피처를 넣지 않고 `v5_cover_base_Z`를 `v5_cover_top_Z`로 둔 평판형을 `guide/.cache/v5/v5_flat.sc`에만 쓴다(모델 폴더에는 안 씀). v5 1차 sha `66a2ec87…`와 같아야 할 필요는 없다(매개변수가 늘었으므로). 보존은 §5-0 스냅샷이 맡는다.

### 2-4. 기대 결과
- 바디 115(방법 A) · 타임라인 450 · 스케치 69 · dof 0 · 오류 0 · 경고 `HOUSING_POSTS_CAND`만(v4부터 있던 경고, `guide/.cache/reference/eval.json`에도 있음).
- 커버 Z [11.5, 19.0]. 커버 부피는 v5 1차(13.07 / 12.06 / 13.61)보다 **줄어든다**(어림: 바닥 3.1 두께 + 턱 1.5 × 2.9 → 조각당 9–11 cm³). 늘어나면 DROP이 안 먹은 것이다.
- plate L/R 부피 38.12 / 40.64 그대로, 이음 쿠폰 부피·bbox 그대로, 58개 미변경 바디 BRep 동일.

---

## 3. 검증 — `inspection/scripts/verify_seam_v5.py`

- `NEW_PARAMS`: `v5_cover_protrude` 제거, §2-1의 8개 추가. `CHANGED_PARAMS` 유지.
- 162–163행의 고정 숫자(18, 11.5, 5)를 매개변수에서 읽도록 바꾼다: 커버 bbox = [`v4_plate_top_Z − TBD_cover_boss_H`, `v5_cover_top_Z`], `TBD_cover_T` = 6.0.
- **새 해석 검사** `cover_levels`:
  - 다리 자석 포켓 위 살 = `v5_cover_base_Z − (13 + 2 + 0.1)` ≥ 1.0 (양쪽).
  - 보스 자석 포켓 위 살 = `v5_cover_base_Z − 13.6` ≥ 1.0.
- **새 BRep 검사**(`live_shapes()`): 커버 3개의 평면 중 법선 +Z인 면을 모아 Z별 면적을 낸다. Z 19.0(턱 윗면)과 Z 16.1(바닥 윗면) 두 값만 있어야 하고, 합이 창을 뺀 커버 평면 면적과 같아야 한다. 각 Z의 면적을 JSON에 기록(턱 면적 / 바닥 면적).
- **표본점 검사**: §1의 7곳(앞 3, 뒤 4)에서 커버 바깥면 꼭대기 Z = 19.0, 왼쪽 (−0.393, 54.7)·오른쪽 (285.388, 19.7)에서 = 16.1. 방법: 각 점 바로 안쪽 0.3 mm 위치에서 +Z 레이 또는 `inspect.clearance`로 작은 프로브 박스(0.2×0.2, Z 16.2–18.8)와의 겹침 유무.
- 간섭: `clearance=0.01`로 변경/미변경 간 overlaps 0, 변경 간 overlaps 0(기존).
- 얇은 벽: 커버 `thin_wall_scan` limit 0.8, `wall_min_mm` ≥ 1.0(현재 1.098과 같은 자리여야 함). 바닥 가장자리의 쐐기형 받침(회전 키 옆에서 폭이 0으로 줄어드는 부분)은 `wall_min_mm`가 None이거나 ≥ 1.0이어야 한다(쐐기 끝은 벽이 아니다).
- v4 sha 불변, CSV = 모델, 미변경 58개 BRep 동일, 이음 쿠폰 부피/bbox 동일 — 모두 기존 검사 유지.
- 기록 `inspection/data/seam-v5-verification.json`, `seam-v5-clearance.json` 갱신.

---

## 4. 검토 모델 — `tools/build_assembly_reference_v5.py`, `inspection/scripts/verify_assembly_reference_v5.py`

- 키캡 밑면: 244·246행의 `15.2 + DZ` → `switch_seat_Z + v5_keycap_bottom_above_seat`(원본 모델 params에서 읽음; 11.3 + 6.0 = 17.3). 윗면도 같은 양(+1.8)만큼 올려 키캡 높이는 유지한다. 평평한 OEM 참고 형상은 그대로(사용자 요구).
- 매니페스트 `assembly_reference_v5.json`에 `cover_base_Z`, `cover_top_Z`, `keycap_bottom_rest_Z`, `skirt_cover_H`, `cover_top_above_rim`, `cover_base_above_rim` 추가. `CASE_V5_*` 유지.
- 검증 스크립트:
  - 66–69행 돌출 4 고정 → `cover_top − rim = v5_cover_top_above_rim`(5.0), 새로 `cover_base_above_rim`(2.1)을 바닥 평면 Z에서 확인.
  - 키캡 ↔ 커버(+하우징): 쉴 때 ≥ 1.0(기대 1.000), 4 mm 눌림 ≥ 1.0(기대 ≥ 1.03). 키캡 ↔ 케이스 ≥ 2.6.
  - **`pressed_vs_plate`를 제외 항목에서 실제 검사로 전환**: overlaps 0, 최소 거리 = 0.3(assert ≥ 0.25). 123–126행의 "reference cap sits too low… excluded" 문구 삭제, 대신 "r2 근거 착좌 + 6.0, upper plate 1.7 → 0.3".
  - 새 보고값 `skirt_cover_rest_mm = cover_top − cap_bottom_rest` = 1.7, `cap_bottom_above_rim`.
- 기록 `inspection/data/assembly-reference-v5-verification.json`.

---

## 5. 내보내기 — `tools/export_seam_v5_review.py`

0. **먼저 스냅샷**: `model/review_v5/flat_Z18/`에 현재 `46es_mount_seam_v5.sc`(sha 66a2ec87…)와 커버 3개 STEP을 복사하고 README 한 줄("v5 1차 평판 Z 18, 2026-11-06, 두 단 커버로 바뀌기 전").
1. 재내보내기(커버 3 + plate 2 + changed STEP). plate 파일은 바뀌지 않아야 한다(sha 비교해서 기록).
2. `model/parameters_seam_v5.csv`, `inspection/data/seam-v5-exports.json`, `seam-v5-thin-wall.json` 갱신.
3. `model/review_v5/README.md` 표의 커버 부피·최소 벽 갱신, flat_Z18 행 추가.

---

## 6. 가이드 — `guide/guide_v5.json`, `guide/assembly_v5.json` → `guide/out_v5`

- 요약 카드 490–491행 `"+4 mm"` → `"+2.1 / +5.0 mm"`, 본문 "바닥 Z 16.1(테두리 + 2.1), 창 둘레 턱 Z 19.0(키캡 옆면 1.7 덮음)".
- 구조 층: 커버 Z 11.5–19.0, 바닥·턱 두 줄.
- 이슈: `v5-rim`(732행) 제목·본문을 두 단 기준으로. `nail`(802행) "노출 4 mm" → "바닥 2.1 + 턱". `v5-travel` 본문에 "참고 키캡을 착좌 + 6.0으로 올려 눌림 ↔ plate 0.3 검사" 추가. 새 이슈 `v5-front-bezel`: 앞·뒤 7곳 베젤 1.16–2.76 → 그 구간은 턱 높이로 선다(§1 표 인용).
- 렌더 추가: `sec-collar` = 단면 `x=161.6`(앞 베젤 1.155 자리), show `@no_switches @keycaps @housing`, 카메라는 `sec_legmag`를 복제해 target [161.6, 4, 15], distance 34. 가능하면 `sec-side`(단면 `x=15`, 왼쪽 바닥이 보이는 곳)도.
- 자석 단면 `sec-legmag` 캡션에 "포켓 위 살 1.0(바닥 16.1)".
- 로그(1445행) 항목에 "2차: 두 단 커버, 참고 키캡 +1.8, B 쿠폰 1.7".
- `assembly_v5.json` 465행 커버 노트·620행 case_hint: "바닥 Z 16.1, 턱 Z 19.0".
- 빌드: `guide/` 폴더에서 `python build_guide.py --spec guide_v5.json --out out_v5`(`guide/README.md` 10행). 확인은 헤드리스 Chrome `--dump-dom`(playwright 없음), 포트는 8791 이상, 끝나면 서버를 죽인다. v4 출력(`guide_v4.json`)이 바뀌지 않았는지 한 번 더 diff.

---

## 7. 문서

- `docs/v5-cover-magnet-margin-2026-11-06.md`: 제목 "커버 4 mm 돌출" → "두 단 커버(바닥 +2.1, 턱 Z 19)". §1을 결정 경위로 다시 쓴다: 4 mm(요청) → r2 확정 최소 3(사실) → 돌출 최소화 + 키캡 쪽 상승(요청) → §1 제약 → 두 단. 새 §6 "두 단 커버"(수치표, 피처, 검증값). §5 upper plate에 참고 키캡 +1.8과 0.3 검사 추가. 변경 바디 표(커버 3개만, plate 변동 없음). 남는 물리 확인은 §11로 교체.
- `model/README.md` v5 절: 커버 두 줄 수정, "커버 부피 감소", 참고 키캡, B 쿠폰 1.7.
- `docs/assembly-reference-2026-11-06.md` v5 주석: 돌출 2.1/5.0, 키캡 밑면 17.3.
- `model/review_v5/README.md`: §5.
- `model/samples/README.md` 38·67행과 `model/print_v4/README.md` 22행: §8.
- 이 계획 문서 맨 위 상태 줄을 "수행함(날짜)"로 바꾸고 결과 수치를 §12에 적는다.

---

## 8. B 쿠폰 — `model/samples/46es_sw_hole_sample.sc`

1. `SMP_upper` 2 → 1.7 (`parameters.change` 또는 document.json 직접 수정 후 `solidcraft-cli run`). 다른 값은 그대로.
2. 부피: 행 C 셀 수 × 16.5² × 0.3만큼 **늘어난다**(개구가 얕아지므로). 셀 수는 모델에서 세고 손계산과 맞춘다. bbox 불변.
3. order1 재내보내기: `46es_v4_sw_hole_coupon.stl/.step` (STL은 `python -I tools/orient_print_stl.py`로 홀 면 아래, print_v4/README 181행 절차). 보스 탭은 같은 파일의 다른 바디라 바뀌지 않지만 같이 내보내도 된다(sha 비교).
4. README 두 곳 갱신 + print_v4/README 표의 부피. 파일 이름은 v4 유지, 주석 "행 C upper 1.7 = v5 plate".
5. `thin_wall_scan`으로 쿠폰 최소 벽 ≥ 1.0 재확인(행 C 홀 층 1.5 유지라 바뀔 것 없음).

---

## 9. 메모리

`project-46es-measurement-pending.md`에 2차 결과(수치·sha·남은 확인) 한 문단 추가, 계획 문서 포인터를 결과 포인터로 바꾼다. 계획 단계의 메모는 이미 적어 두었다.

---

## 10. 순서 · 명령 · 수용 기준

순서: §5-0 스냅샷 → §2 프로브(방법 A) → §2 빌드 → §3 검증 → §4 검토 모델 + 검증 → §5 내보내기 → §8 B 쿠폰 → §6 가이드 → §7 문서 → §9 메모리 → 보고.

```
python tools/build_seam_v5.py
python -B inspection/scripts/verify_seam_v5.py
python tools/build_assembly_reference_v5.py
python -B inspection/scripts/verify_assembly_reference_v5.py
python tools/export_seam_v5_review.py
cd guide && python build_guide.py --spec guide_v5.json --out out_v5
```

수용 기준(모두 만족해야 "완료"):
- [ ] 커버 평면 윗면 Z가 19.0과 16.1 두 값뿐, 다리 포켓 위 살 1.0, 보스 포켓 위 살 2.5.
- [ ] §1의 7곳 바깥면 꼭대기 19.0, 좌·우 표본점 16.1.
- [ ] 키캡 ↔ 커버 ≥ 1.0(쉴 때/눌림), ↔ 케이스 ≥ 2.6, 눌림 ↔ plate ≥ 0.25(기대 0.3), 겹침 0.
- [ ] 미변경 바디 58개 BRep 동일, plate 부피 불변, 이음 쿠폰 불변, v4 sha 불변.
- [ ] 커버 최소 벽 ≥ 1.0(`wall_min_mm`), 부피 v5 1차보다 작음.
- [ ] STL 연결 성분 1, 열린 모서리 0, CAD 대비 부피 오차 < 0.01 %.
- [ ] 가이드 out_v5 빌드 성공, 새 렌더 2개, v4 출력 불변.
- [ ] 커밋·배포·발주 없음. 스냅샷 폴더 존재.

---

## 11. 남는 물리 확인 (사용자, 모델 밖)

1. **r2 키캡 스커트 높이** — 이것이 D3을 확정한다. r2 조립 상태에서 upper plate 윗면 → 키캡 스커트 밑면을 쉴 때와 끝까지 누른 때 잰다. 기대 약 4.0 / 약 0–0.3. 값 g(쉴 때)를 얻으면 `v5_keycap_bottom_above_seat = 2 + g`로 바꾸고 §2–§4를 다시 돌린다.
2. 테두리 높이(지지대 상면 기준 앞·뒤). 14가 아니면 `v5_rim_ref_Z`만 바뀌고 형상은 안 바뀐다(바닥은 자석에서 유도).
3. 앞·뒤 좁은 베젤 7곳(1.16–2.76 × 높이 6.0)의 출력 강도와 휨 — 커버 출력 후 확인. 문제면 그 키만 여유 0.8로 줄이는 안을 다시 올린다(D9 변경은 사용자 결정).
4. 키캡 풀러: 간격 1.0에 턱 깊이 1.7(쉴 때). r2(간격 ≈ 0.3–0.5, 깊이 3.0)에서 쓰던 방법이 그대로 되는지.
5. 투명 레진에서 바닥(3.1)과 턱(1.5 × 2.9)의 시각 차이, 보스·자석이 비치는 모습 — 보스 탭 시험과 함께.

---

## 12. 결과 (2026-11-06 수행)

모델 `model/46es_mount_seam_v5.sc` sha `a61f57fa…`(1차 `66a2ec87…`은 `model/review_v5/flat_Z18/`에 보존, v4 `606d1bd9…` 불변). 방법 A(한 스케치 + 영역 선택 컷)로 성공, 방법 B는 쓰지 않았다. 바디 115 · 타임라인 450 · 스케치 69 dof 0 · 오류 0 · 경고 `HOUSING_POSTS_CAND`만 · 매개변수 213.

### 12-1. 수용 기준(§10)

| 기준 | 결과 | 수치 |
|---|---|---|
| 커버 윗면 Z 두 값, 포켓 위 살 | ○ | 위를 보는 평면 Z = {16.1, 19.0}뿐(커버 3개 모두). 다리 포켓 위 살 1.0, 보스 포켓 위 살 2.5 |
| §1 7곳 바깥면 꼭대기 19.0, 좌·우 16.1 | ○ (기하 예측과 측정 일치; **§3·§10 표현 정정**) | 베젤 < 1.5인 3곳(앞 X 144.4, 뒤 X 67.6 / 194.2) = **19.0**. 베젤 2.66–2.76인 3곳(앞 X 243.0, 뒤 X 45.1 / 216.7) = 16.1 + 바깥쪽 받침 1.16–1.26 뒤에 턱(D4대로). 앞 X 116.0(2.25u 썸키 1.42)은 r2 창이 가장자리까지 열려 커버 살 없음. 왼쪽 (−0.093, 54.7)·오른쪽 (285.088, 19.7) = **16.1** |
| 키캡 ↔ 커버 ≥ 1.0, ↔ 케이스 ≥ 2.6, 눌림 ↔ plate ≥ 0.25, 겹침 0 | ○ | 커버 1.000(쉴 때) / 1.000(4 mm 눌림), 케이스 2.628, 눌림 ↔ plate **0.300**(46개, 겹침 0), 겹침 0 |
| 미변경 58바디 BRep 동일, plate 불변, 이음 쿠폰 불변, v4 sha 불변 | ○ | 58 동일. plate L/R 부피 38,120.821 / 40,636.401, BRep·STL·STEP 1차와 동일. 이음 쿠폰 부피·bbox v4와 동일 |
| 커버 최소 벽 ≥ 1.0, 부피 1차보다 작음 | ○ | `wall_min_mm` L 1.000 / T 1.098 / R 1.000 (1.0 = 다리 자석 포켓 위 살). 부피 9.29 / 8.65 / 10.16 cm³ < 13.07 / 12.06 / 13.61 |
| STL 성분 1, 열린 모서리 0, 부피 오차 < 0.01 % | ○ | 5개 모두 성분 1, 모서리 0, 오차 ≤ 0.0036 % |
| 가이드 out_v5 빌드, 새 렌더 2, v4 출력 불변 | ○ | 아래 12-4 |
| 커밋·배포·발주 없음, 스냅샷 폴더 | ○ | HEAD 0880d22 그대로. `model/review_v5/flat_Z18/`(모델 + 커버 STEP 3 + README) |

### 12-2. 커버 수치

| 커버 | 부피 cm³ (1차) | 바닥 면적 / 턱 면적 mm² | 최소 벽 | 부피 예측 오차 |
|---|---:|---:|---:|---:|
| L | 9.29 (13.07) | 2169.5 / 341.7 | 1.000 | 3e-7 |
| T | 8.65 (12.06) | 1989.4 / 370.5 | 1.098 | 1e-7 |
| R | 10.16 (13.61) | 2088.7 / 511.5 | 1.000 | 5e-7 |

예측 = 1차 부피 + 윗면 면적 × (19 − 18) − 바닥 면적 × 2.9. 각 커버의 바닥 + 턱 면적 = 1차 윗면 면적(2511.2 / 2359.9 / 2600.2). 돌출 확인값: 바닥 − 테두리 **2.1**, 턱 − 테두리 **5.0**(검토 모델 bbox 테두리 14.000, 커버 19.000). 키캡 밑면 17.3(테두리 + 3.3), 턱이 스커트를 덮는 높이 1.7(쉴 때) / 5.7(4 mm 눌림).

DROP 영역: 선택 2(바깥 성분 + 갇힌 포켓 1: X 74.6–79.1, Y 25.3–32.8, 10.8 mm², 내접 폭 2.09 — 규칙 경계값, §11-6 추가), 선택 안 함 8(회전 키 모서리의 0.05 래스터 조각, ≤ 0.04 mm²).

### 12-3. B 쿠폰

`SMP_upper` 1.7, sample sha `67014f98…`. **부피 불변** 55,737.43 mm³(§8의 "+571.7" 예상은 틀림, §13), bbox 불변, 홀 층 Z 6.5–8.0 → 6.8–8.3, 셀 7. order1 쿠폰 STL(홀 면 아래, 145.35 × 74.15 × 10, 최소 벽 1.5) + STEP 재내보냄, 보스 탭도 재내보냄(부피 8,968.83 불변, 최소 벽 1.299). `seam-v4-print-set.json`·`seam-v4-mjf-thin-wall.json` 갱신, `verify_seam_v4.py` 통과.

### 12-4. 가이드·문서

`guide/out_v5` 빌드 성공, 렌더 19(새 `sec-collar` X 144.4, `sec-side` X 15). v4 출력 `guide/out`은 건드리지 않음(index.html 14:10, 이 세션 이전). 문서: v5 문서 재작성, `model/README.md`, `model/review_v5/README.md`(flat_Z18 행), `model/samples/README.md`, `model/print_v4/README.md`, `guide/README.md`, `docs/assembly-reference-2026-11-06.md`, 이 문서 §12·§13. 메모리 갱신.

### 12-5. 남는 물리 확인

§11 그대로 + 갇힌 포켓(§11-6, v5 문서 「남은 실물 확인」 6). r2 실측(upper plate 윗면 → 키캡 스커트 밑면, 쉴 때)은 아직 없다 → `v5_keycap_bottom_above_seat` 6.0 유지.

---

## 13. 이번 세션에서 걸린 함정 (새 세션 참고)

- Bash 히어독에 따옴표가 섞인 파이썬을 넣으면 깨진다 → 스크립트는 Write로 쓰고 실행.
- 스크래치패드 경로는 `cygpath -w`로 바꿔 파이썬에 넘긴다. cp949 콘솔에서 `−`(U+2212) 출력이 터진다 → `PYTHONIOENCODING=utf-8`.
- 8767 포트는 다른 프로세스가 쓴다 → 8791 이상, 끝나면 내 서버만 죽인다.
- `--out` 경로 뒤에 백슬래시 누락으로 폴더가 합쳐진 적 있다.
- 검토 모델에서 Wilmore 하우징과 `REF_SW_ASSUMED_*`는 원본 대비 "사라진 바디"로 허용되어 있다.
- 이음 쿠폰 L/R은 plate 복사본이라 plate 피처가 바뀌면 BRep이 달라진다 → 부피·bbox 동일 검사로 분류돼 있다.
- repo는 `core.autocrlf=true`. 매니페스트는 커밋 때만 재생성.

(2차 수행 세션에서 추가)

- **document.json에는 점 선택(`profiles: [{point}]`) 저장 형식이 없다**(`{"type":"all"}` 또는 `{"type":"curves","loops":[…]}`뿐). 영역 선택 컷은 시드 문서에 스케치만 넣고, `solidcraft-cli run drop.json --in seed.sc --save out.sc`로 `solid.extrude` 명령을 얹어 만든다. 명령이 점 선택을 둘레 곡선 선택으로 바꿔 저장하므로 재평가에 안정적이다. 겹치는 사각형 47개가 든 한 스케치에서도 영역 선택이 됐다(프로브 a 통과).
- **SCBREP04 캐시의 면 루프는 바깥 법선 기준 시계 방향이다.** 평면 면의 신발끈 합은 +Z 면에서 음수가 나온다 → 부호를 뒤집어야 "위를 보는 면"이 잡힌다(`read_sc_cache.shell_summary`가 `abs(volume)`을 취하는 이유).
- **§1의 베젤 표는 키 중심이 아니라 회전 창의 모서리 자리다.** 2u 썸키(161.6, 14.4)의 1.155는 X 144.4, 2.25u 썸키의 1.42는 X 116.0에 있다. 프로브를 키 중심 X에 두면 엉뚱한 값(바닥 16.1)이 나온다. 또 X 116.0은 r2 창(SK34)이 가장자리까지 열려 커버 살이 없다. §1은 창 ↔ 외곽의 순수 기하 거리라 r2 창이 이미 뚫린 곳을 가리지 않았다.
- **§3·§10의 "7곳 꼭대기 19.0"은 D4와 맞지 않는 표현이다.** 베젤 2.66–2.76인 3곳은 턱(1.5)이 외곽에 못 미쳐 바깥쪽 1.16–1.26이 바닥(16.1)으로 남는다. D4("베젤 < 2.5 → 턱이 바깥면까지")는 키캡 기준 2.5 = 창 기준 1.5라 맞다. 검증은 "베젤 < 1.5 → 19.0, 아니면 16.1 + 받침, r2 창이 열린 곳 → 살 없음"으로 바꿔 기하 예측과 측정이 일치함을 확인했다.
- **B 쿠폰 부피는 `SMP_upper`에 무관하다.** 행 C 아래 개방(`RELIEF_C*`)이 홀 층 밑면까지 열려 있어, 열린 기둥 안 재료는 홀 층 고리 1.5 × (16.5² − h²)뿐이다. §8의 "+셀 수 × 16.5² × 0.3"은 틀렸다(0 변화). 홀 층 Z 6.5–8.0 → 6.8–8.3으로 확인했다. Z 6.5는 행 D 카운터보어 바닥이라 남는다.
- 보스 탭을 같은 파일에서 다시 내보내면 형상이 같아도 STL 메시가 달라진다(삼각형 분할 차이, 부피 8968.86 vs 8968.98). sha 비교로 "불변"을 말할 수 없으니 부피·bbox·최소 벽으로 비교한다.
- `sed -i`는 스크래치패드(다른 드라이브) 파일에 "Invalid cross-device link"로 실패한다 → Edit 도구로 고친다.
- `scipy.ndimage.find_objects(labels, n)[lab-1]`로 써야 한다. `find_objects(labels == lab)`는 bool 배열이라 TypeError.
- 가이드 spec의 `{{p:v5_cover_protrude}}` 같은 삭제된 매개변수 토큰은 빌드를 멈춘다 → 매개변수를 지울 때 spec을 grep한다.
