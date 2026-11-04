# 46es 3D 프린팅 케이스 — 제작 모델 준비 (실측 대기)

> **제작용 아님.** 여기의 값은 대부분 자리표시이거나 미검증 참고값이다. 바디는 PSD60 자리에 둔 **하우징 대용 바디 1개**(Wilmore STL 기반, 간섭 확인용), **46es 부품 바디 6개**(프레임·plate·스탠드오프·커버 3조각, 이름 `_DRAFT_TBD`), **점유 영역 바디 2개**(컨트롤러·USB 아웃렛, 자리표시)다. 2026-11-04 후반 작업으로 부품 바디에는 논의한 구조(프레임 중앙 개방·리브·장공·육각 포켓·컨트롤러 포켓·USB 노치, plate 3층(upper plate 16.5 개구 / 14.0 홀 1.5T / 하면 릴리프)·카운터보어·커버 단차, 커버 r2 3조각 창·립)가 모두 들어 있고, **실측값만 비어 있는 상태**다. 해당 부품의 실측(`measurements.csv`)이 끝나기 전에는 출력 파일을 만들지 않는다(예외: B 단계 시험 쿠폰 `samples/`).

현재 상태 (2026-11-04 마지막): 매개변수 139개(미확정 `TBD_`·`CAND_` 88개), 스케치 12개(모두 자유도 0), 피처 96개, 바디 9개, 타임라인 오류 0. 2026-11-04 마지막 사용자 결정 3건: **스태빌라이저 사용 안 함**(`stab_2u` 0 확정), **Pro Micro는 키보드 중앙 하단 키 없는 공간**(SO6 바로 뒤, 중앙 세로 바 위), **커버 창과 plate 구조는 아크릴 r2 형상 그대로**(DWG 적층 아래→위 P0 링 2T · P1 중간 프레임 5T · P2 plate 1.5T · P3 upper plate 2T · P4 cover 5T 3조각 · P5 upper cover 2T 3조각). B 단계 스위치 홀 쿠폰은 `samples/`에 내보냈고, A 단계 체결 시험 지그는 `jigs/`에 형상만 있다. **다음 작업은 PSD60 실측과 쿠폰 출력이다.** 실측값이 나오면 하우징 대용 바디와 부품 바디가 함께 따라간다(예외: DXF로 넣은 키 위치 스케치 3개는 고정 숫자, 아래 표 참조). 근거는 `../inspection/46es_r2_dwg_inspection.md`(DWG), `../inspection/wilmore/README.md`(Wilmore)에 있다.

| 파일 | 내용 |
|---|---|
| `parameters.csv` | 치수 입력용 매개변수 138개. `TBD_` = 미확정, `CAND_` = GH60 후보 좌표(추정), `REF_` = DWG r2 참고값, `REF_WIL_` = Wilmore STL 추정값(PSD60 아님), `REF_draft_` = 초안용 가정값(근거 없음). 주석에 근거와 측정 ID를 적었다. SolidCraft `parameters.import` 형식이다. |
| `measurements.csv` | 실측 시트 M01–M21. 측정값 칸은 비어 있다. `현재 후보값`에 Wilmore 값을 함께 적었다. |
| `46es_draft_sketches.sc` | SolidCraft 디자인. 매개변수, 스케치 11개, 피처 94개, 바디 7개. 스케치는 모두 자유도 0 |
| `46es_parts_v3_iso.png` / `46es_frame_v3_top.png` / `46es_cover_v4_top.png` / `46es_plate_v3_top.png` / `46es_plate_v3_keys_iso.png` | 2026-11-04 마지막 렌더(진짜 상면, 카메라 pitch +90°): 전체(하우징 제외), 프레임(컨트롤러 포켓 중앙 하단), 커버 3조각(r2 P4 형상), plate(16.5 upper plate 개구), plate 키 몇 개 확대(3층 구조) |
| `46es_cover_v3_top.png` | 2026-11-04 후반 렌더: 커버 실루엣 창(직선 메움 16 + R0) 시절. 커버 창을 r2 형상으로 바꾸면서 폐기된 안의 기록 |
| `46es_parts_v2_iso.png` / `46es_frame_v2_top.png` / `46es_cover_v2_top.png` / `46es_parts_v2_section_usb_x18.png` | 2026-11-04 후반 렌더: 전체, 프레임만, 커버(닫힘 R8 시절), USB 개구부 위치 X=18.7 단면. **주의: `_top` 2장은 카메라 pitch −90°로 찍혀 실제로는 아래에서 본 거울상이다** |
| `46es_draft_parts_iso.png` / `46es_draft_parts_section_x142.png` | 초안 단계(같은 날 전반) 렌더 — 통판 프레임·벽형 커버 시절 |
| `46es_draft_sketches_top.png`, `46es_housing_ref_wilmore_iso.png` | 더 이른 단계 렌더 |
| `samples/` | B 단계 스위치 홀 시험 쿠폰(`46es_sw_hole_sample.sc`, 홀 13.7–14.3 × 행 A 노치/행 B 개방 포켓, M2 구멍). 시험물이며 부품이 아니다. STL/STEP 내보냄, 미발주 |
| `jigs/` | A 단계 케이스 체결 시험 지그(`46es_jig_A_case_holes.sc`, 2.5T 판 + 구멍 6 + 창 2). 형상만, STL 미생성 |
| `../tools/make_key_dxf.py` | 키 위치 DXF 생성기(`sq` 정사각형 = SK22 14.0·SK24/SK25 16.5, `notch` 십자·`silhouette` 블록 실루엣은 2026-11-04 마지막 이후 미사용). `TBD_pcb0_dx/dy`가 바뀌면 `sq 14`·`sq 16.5`로 DXF를 다시 만들어 SK22·SK24·SK25를 교체한다 |
| `../tools/make_r2_cover_dxf.py` | r2 DWG 모델 공간 DXF에서 P4(5T) 3조각 경계를 읽어 커버 창 2개(판 변 바깥으로 3 연장한 닫힌 다각형) DXF를 만든다 → SK34. P4와 P5의 조각 윤곽이 같음을 함께 확인한다 |

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
| `SK22_PLATE_HOLES_REF_r2_NOT_FOR_PRODUCTION` | plate 하면 | r2 P3 중심·회전각의 14.0 정사각형 46개(고정 숫자, `../inspection/derived/REF_r2_keys_sq14_gh60.dxf`). 매개변수를 따르지 않음 |
| `SK24_PLATE_UPPER_OPENINGS_REF_r2_P3_NOT_FOR_PRODUCTION` | plate 상면 | **upper plate 층**: 같은 중심·회전각의 16.5 정사각형 46개(`REF_r2_keys_sq16p5_gh60.dxf`, 고정 숫자) = r2 P3(2T) 개구부. 깊이 `TBD_upper_plate_T`(2)로 컷 |
| `SK25_PLATE_LOWER_RELIEF_REF_r2_NOT_FOR_PRODUCTION` | plate 하면 | 같은 16.5 정사각형 46개(같은 DXF). 높이 `TBD_sw_notch_H`(= `TBD_plate_T − TBD_upper_plate_T − TBD_sw_ledge_T` = 1.5)로 위로 컷. 걸쇠 아래 공간(r2에서는 P1 5T 큰 개구부의 역할) |
| `SK34_COVER_WINDOWS_REF_r2_P4_NOT_FOR_PRODUCTION` | 커버 상면 | **r2 P4(5T)/P5(2T) 3조각 커버의 조각 사이 창 2개**(좌 30꼭짓점, 우 40꼭짓점, `REF_r2_cover_windows_P4_gh60.dxf`, 고정 숫자, r2 좌표 − (0.693, 0.667)). 창은 r2처럼 위·아래 변까지 열려 있어(위 68.2~87.3 / 174.2~193.4, 아래 100.6~117.8 / 145.0~157.3) 커버가 **왼쪽 L형·가운데 T형·오른쪽 3조각**으로 나뉜다. 컷 깊이 `TBD_cover_T + TBD_cover_lip_H`(립까지 관통) |
| `SK11_SO_HEX_POCKETS_TBD` | `TBD_frame_T − TBD_so_pocket_D` | 스탠드오프 육각 포켓 6개(맞변 `TBD_so_AF + TBD_so_pocket_clr`, 중심 식 `REF_SO_dXn − TBD_pcb0_dx`). 매개변수를 따름. 상면 쪽(Z 1.5~3) 포켓임을 면 측정으로 확인 |

삭제된 스케치: `SK32_COVER_WINDOWS_REF_r2…`(20.0 정사각형 46개, 2026-11-04 후반 → SK33), `SK33_COVER_SILHOUETTE_REF_r2…`(키 블록 실루엣 창 2개, 2026-11-04 마지막 → SK34, 생성기 `make_key_dxf.py silhouette`와 DXF `REF_r2_cover_silhouette_gh60.dxf`는 기록용으로 남김), `SK23_PLATE_NOTCH_REF_r2…`(걸쇠 노치 십자 46개, 2026-11-04 마지막 → SK24/SK25 3층 구조로 대체).

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

### 부품 바디 `*_DRAFT_TBD` (2026-11-04, 후반 갱신)

논의한 구조를 모두 3D로 넣은 상태다. **출력하지 않는다**(§4 게이트). 실측 후 `TBD_` 값을 바꾸면 그대로 따라온다. 예외는 DXF로 넣은 고정 스케치 3개(SK22 홀, SK23 노치, SK33 커버 창)와 `PLATE_ISLAND_CHAMFER`의 모서리 선택점(아래 주의). 좌표는 GH60 기준점, Z 0 = 하우징 지지대 상면.

| 바디 | 피처(타임라인 순) | Z 범위 | 내용 · 따르는 매개변수 |
|---|---|---|---|
| `FRAME_DRAFT_TBD` | `FRAME_DRAFT_TBD`(SK10 돌출) → `FRAME_WINDOW`(중앙 개방) → `FRAME_BAR_CENTER`·`FRAME_BAR_H01`·`FRAME_BAR_H04`(바) → `FRAME_BOSS_H01…H04`, `FRAME_BOSS_SO1…SO6`(보스) → `CTRL_POCKET_RING` → `CASE_HOLE_H01/H05/H06`(원형), `CASE_SLOT_H02/H03/H04`(+`_A`,`_B` 끝 원, X 방향 장공) → `CASE_CB_*`(상면 카운터보어) → `SO_HOLE_1…6` → `USB_NOTCH_TBD` → `CTRL_POCKET_CUT`·`CTRL_LIP_CUT` → `SO_HEX_POCKETS`(SK11 컷) | 0 → `TBD_frame_T`(3) | 테두리 폭 `TBD_frame_rib_W`(8), 중앙 세로 바 `TBD_frame_bar_W`(10, H02 장공 + 스탠드오프 3·6), H01은 왼쪽 테두리로 가는 가로 바, H04는 뒤 테두리로 가는 세로 바, 보스 Ø`TBD_frame_boss_D`(10). 케이스 나사 Ø`TBD_case_screw_D + clr`(2.4), 장공 길이 `TBD_case_slot_L`(5), 카운터보어 Ø`TBD_case_head_D`(4)×`TBD_case_head_H`(1). 스탠드오프 Ø3.3 + 육각 포켓 맞변 5.0×깊이 `TBD_so_pocket_D`(1.5). USB 노치 폭 `TBD_usb_outlet_W + 2·TBD_usb_glue`(14) × 깊이 `TBD_usb_keepout_D`(15), 뒤 테두리 관통. 컨트롤러 포켓(2026-11-04 마지막 이동): 벽 `TBD_ctrl_wall`(3, 1.5에서 키움), 여유 `TBD_ctrl_clr`(0.3), 턱 `TBD_ctrl_lip_W`(1)×`TBD_ctrl_lip_T`(1), 위치 `TBD_ctrl_X/Y` = 키보드 중앙 하단(링 X 111.1~150.7, Y 7.63~32.2: 앞벽이 앞 테두리 안쪽 변에 붙고 SO6 보스·중앙 세로 바와 합쳐짐). 포켓이 중앙 세로 바를 끊는 대신 링 양쪽 벽 3×3이 바를 잇는다. 포켓 컷 앞변(Y 10.63)과 SO6 육각 포켓(Y ≤ 9.02) 사이 살 1.6 |
| `STANDOFFS_DRAFT_TBD` | `STANDOFF_1…6`(원기둥, 한 바디 6조각) | `TBD_frame_T − TBD_so_pocket_D` → `TBD_frame_T + TBD_standoff_H` | 부품 길이 = 포켓 깊이 + 스탠드오프 높이 = 6.5. Ø = `TBD_so_AF × 1.1547` |
| `PLATE_DRAFT_TBD` | `PLATE_DRAFT_TBD`(SK20) → `PLATE_SW_HOLES_REF_r2`(SK22) → `PLATE_CB_SO1…6` → `PLATE_RABBET_L/R/F/B` → `PLATE_ISLAND_CHAMFER` → `PLATE_UPPER_OPENINGS_REF_r2_P3`(SK24) → `PLATE_LOWER_RELIEF_REF_r2`(SK25) | 8 → 13 | **r2 plate + upper plate를 한 부품으로 합친 3층 구조**(사용자 2026-11-04 마지막): 위 `TBD_upper_plate_T`(2) = 16.5 개구(r2 P3, 스위치 상부 하우징 15.6이 들어감) / 가운데 `TBD_sw_ledge_T`(1.5) = 14.0 홀 층(r2 P2 1.5T, 걸쇠가 이 층 아래에 걸림) / 아래 `TBD_sw_notch_H`(1.5) = 16.5 릴리프(걸쇠 공간, r2 P1 역할). 스위치 플랜지는 plate 상면보다 2 아래(Z 11)에 앉는다. 스탠드오프 나사 카운터보어 Ø`TBD_so_head_D`(6)×`TBD_so_head_H`(2). 가장자리 단차(rabbet) 폭 `TBD_cover_wall + TBD_cover_lip_clr`(2.3) × 깊이 `TBD_cover_lip_H`(1), 안쪽 섬 코너 모따기 `TBD_plate_C`. 16.5 개구는 카운터보어·단차와 겹치지 않음(래스터 확인) |
| `COVER_L_DRAFT_TBD` · `COVER_T_DRAFT_TBD` · `COVER_R_DRAFT_TBD` | `COVER_DRAFT_TBD`(SK30 돌출) → `COVER_LIP_L/R/F/B` → `COVER_WINDOWS_REF_r2_P4`(SK34, 컷이 바디를 3조각으로 가름) | 12 → 15 | **평판 베젤** 두께 `TBD_cover_T`(2) + 테두리 립 폭 `TBD_cover_wall`(2)×높이 `TBD_cover_lip_H`(1)가 plate 단차에 앉음(코너 R 구간은 립 없음). 창: **r2 P4/P5 3조각 커버의 형상 그대로**(사용자 2026-11-04 마지막) — 왼쪽 L형(5,749.8 mm³)·가운데 T형(5,176.6)·오른쪽(6,138.9) 조각 사이 두 창이 위·아래 변까지 열림. r2에서 세 조각은 스택 볼트 6곳(= 우리 스탠드오프 SO1~6 위치, P5 Ø3.0 / P4 육각 AF 4.711)으로 고정됐다. 우리 조각에는 아직 구멍이 없다 → 커버 고정 방식 결정 시 같은 6곳에 구멍·포켓 추가가 자연스럽다 |
| `CTRL_KEEPOUT_TBD` | `CTRL_KEEPOUT_PCB` + `CTRL_KEEPOUT_PARTS` | −1.4 → 2.6 | Pro Micro 점유 영역: PCB `TBD_ctrl_L×W×REF_ctrl_pcb_T`(33×18×1.6)가 턱 위, 부품 `TBD_ctrl_H − 1.6`이 아래(하우징 바닥 쪽). 위치(사용자 2026-11-04 마지막: 키보드 중앙 하단 키 없는 공간): `TBD_ctrl_X = REF_SO_dX6 − TBD_pcb0_dx − TBD_ctrl_L/2`(PCB 중심 X 130.88 = ±11° 열 가운데), `TBD_ctrl_Y` = 앞 테두리 안쪽 변 + 벽 + 여유(10.93). PCB X 114.4~147.4, Y 10.9~28.9. 둘째 줄 스위치(110.5, 31.8)·(151.3, 31.8) 발자국과 XY로 4.3씩 겹치지만 PCB 상면 2.6 < 스위치 핀 끝 4.7이라 Z로는 간섭 없음. USB 단이 ±X를 향하므로 연장 케이블은 PCB 끝에서 옆으로 나와 프레임 아래 공간으로 지나 뒤-왼쪽 개구부로 간다 |
| `USB_OUTLET_TBD` | `USB_OUTLET_KEEPOUT` | `TBD_usb_Z ± TBD_usb_outlet_H/2` | 패널형 USB 연장 커넥터 점유 영역 `TBD_usb_outlet_W×D×H`(12×12×8), 뒤 내벽에 붙음. 규격 미확인 자리표시 |

부피(2026-11-04 마지막): 프레임 20,988.2(컨트롤러 포켓 이동 전 21,100.6; 이동 손계산 20,896.8과 91 차이 — 옛 위치 (33, 68)의 링이 기존 살과 그만큼 겹쳐 있었던 것으로 보이며 새 위치 계산은 일치), plate 76,552.0(손계산 76,552.0: 노치 십자 제거 +2,208.0 → 16.5 upper 개구 −7,015 → 16.5 하면 릴리프 −5,261.3), 스탠드오프 901.8(Ø`TBD_so_AF·1.1547` 5.43 × 길이 6.5 × 6), 커버 3조각 합 17,065.2(래스터 17,043~17,056; 실루엣 창 시절 17,263.2, 창 제거 전 55,963.0), 컨트롤러 2,140.8, USB 1,152.0 mm³. 각 단계는 `batch`의 `expect`나 바로 뒤 `measure`로 손계산과 대조했다.

`check_parameters`로 `TBD_pcb0_dx`=1.2, `TBD_so_AF`=5, `TBD_frame_rib_W`=10, `TBD_cover_lip_H`=1.5, `TBD_ctrl_X`=40을 동시에 바꿔 재빌드했을 때 94개 피처가 오류 없이 따라왔고, `PLATE_ISLAND_CHAMFER`만 실패했다(모서리 선택점이 0.5 이상 움직이면 이웃 모서리로 붙음). **실측 후 plate 외곽이 바뀌면 이 피처의 선택점 4개를 새 코너 좌표로 다시 찍는다**(`timeline.edit`).

2026-11-04 마지막 결정·변경(사용자 결정 3건 반영):
- **스태빌라이저 사용 안 함.** `stab_2u` = 0 확정(접두어 제거). 2.25u·2u 썸키는 스위치만으로 지지한다. plate·커버에 스태빌라이저 컷 없음.
- **Pro Micro 위치 = 키보드 중앙 하단 키 없는 공간.** 좌·우 썸키(2.25u / 2u) 사이, 스탠드오프 6 바로 뒤에 PCB(33×18)를 X 방향으로 눕혀 둔다(`TBD_ctrl_X/Y` 식 참조). plate 아래 빈 공간은 X 104.6~153.4(Y < 23.5)라 33 길이가 둘째 줄 스위치 발자국과 끝에서 4.3씩 겹치지만, PCB 상면(Z 2.6)이 스위치 핀 끝(Z 4.7)보다 낮아 간섭은 없다. 중앙 세로 바가 포켓에 끊기므로 포켓 벽을 3으로 키웠다. 하우징 바닥까지 깊이(`TBD_support_H`, Wilmore 6.2)는 USB 플러그가 PCB 부품면 아래로 나오는 높이(약 7)에 못 미칠 수 있다 → M05·M15에서 확인.
- **커버 창 = 아크릴 r2 P4(5T)/P5(2T) 3조각 형상 그대로.** 키 블록 실루엣 생성 방식(R8 → 직선 메움 + R0)은 폐기하고 r2 조각 경계를 그대로 썼다(`tools/make_r2_cover_dxf.py`). 두 창이 위·아래 변까지 열려 커버가 L형·T형·오른쪽 3조각이 된다. r2에서는 세 조각을 스택 볼트 6곳으로 고정했다(P5 Ø3.0, P4 육각 AF 4.711) — 우리 스탠드오프 위치와 같으므로 커버 고정 방식을 정할 때 같은 자리에 구멍을 내면 된다(아직 없음). DWG 판 순서(위→아래 그림 배치 = 적층 아래→위): P0 2T 링 · P1 5T 중간 프레임 · P2 1.5T plate · P3 2T upper plate · P4 5T cover · P5 2T upper cover.
- **plate = r2 plate(1.5T, 14.0) + upper plate(2T, 16.5)를 한 부품으로.** 두께 5는 유지하고 위 2(16.5 개구) / 가운데 1.5(14.0 홀) / 아래 1.5(16.5 릴리프) 3층으로 바꿨다. 걸쇠 노치 십자(fidget식, SK23)는 삭제. 스위치 플랜지는 plate 상면보다 2 아래에 앉으므로 키캡 높이도 2 낮아진다(커버 상면 Z 15, 키캡 하단 약 Z 17.6). 쿠폰 행 B(개방 16.5 포켓)가 이 구조에 해당한다.
- **렌더 카메라 주의.** 이 세션 MCP의 `screenshot camera.pitch`는 +π/2가 위에서 본 평면도다. 이전 `_top` 렌더(v2, cover v3)는 −π/2로 찍어 아래에서 본 거울상이었다. v3/v4 렌더부터 바로잡았다(육각 포켓이 보이는 쪽이 상면).

2026-11-04 후반에 드러난 점:
- **벽 있는 커버는 성립하지 않는다.** 뒤쪽 윗줄 키캡(회전 −6°/+6° 열, ry 83.2) 모서리가 하우징 내벽에서 2.15밖에 안 떨어져 있어, 간격 0.3 + 벽 2가 들어갈 수 없다. 커버를 **평판 베젤 + plate 단차 립**으로 바꿨다(`TBD_cover_H = TBD_cover_T`, `REF_draft_cover_H`는 기록용).
- 커버 창은 처음에 키캡 18 + 간격 1 기준의 열 단위 창(14 + 7개)으로 만들었으나, 뒤 레일 1.41 < 1.6으로 두 열이 가장자리까지 열리고 열 경계마다 쐐기 살이 남아 사용자 요청(위·아래·좌·우·가운데 구역만, 키 배치 안에는 베젤 없음)으로 **키 블록 실루엣 창 2개**로 바꿨다. 처음엔 R8 원판 닫힘 하나로 틈 메움과 모서리 둥글림을 같이 했는데 계단마다 R8 호가 생겨 곡선이 많았다(사용자: 반지름을 확 줄일 것). 지금은 **가로·세로 직선 닫힘(`TBD_cover_fill_L` 16)으로 틈을 직선으로 메우고 오목 모서리는 둥글리지 않는다(`TBD_cover_close_R` 0, R2 → 0.5를 거쳐 사용자 요청으로 0)**. 메워지는 범위는 R8 때와 거의 같고(창 면적 19,417 → 19,342), 모서리만 직각이 됐다. 창 외곽선은 직선 84개(좌 36 + 우 48)뿐이다. R2 원판 닫힘만 쓰면 +7°/+3° 열 사이에 폭 약 1의 베젤 쐐기가 남아 직선 메움이 필요하다. 창 기준은 r2 P3 층과 같이 스위치 상부 개구 16.5 + 여유 1.0이라 키캡(18)은 창 경계를 0.25 덮고 베젤 상면보다 약 5 위에 떠 있다(눌렀을 때 약 3, M17로 확인).
- 키캡 폭: 사용자 확인(2026-11-04) **맨 아랫줄 왼쪽부터 1.25u · 1u · 2.25u · 2u · 1u · 1u** → `tools/make_key_dxf.py`의 `WIDTHS_U`에 (37.1, 19.1) 1.25u, (97.1, 15.7) 2.25u, (162.3, 15.0) 2u로 반영(펌웨어 JSON의 1.75u 표기와 다름, 현물 기준). 화살표 4키는 1u. 실루엣 창에서는 썸키 창 외곽선에만 영향.
- **가변 폭 키**(사용자 2026-11-04): PgUp·PgDn과 맨 아랫줄 6키는 키캡 보유 상황에 맞춰 폭을 바꿀 수 있어야 한다 → 커버 창은 실제 폭이 아니라 **수용 폭**(`ENVELOPE_U` = 실제 + 0.5u, PgUp·PgDn 1.5u)으로 그린다. 키캡이 수용 폭보다 좁으면 그 둘레로 plate 상면이 보인다. 실제 폭·수용 폭 모두 `tools/make_key_dxf.py` 표에서 바꾼 뒤 DXF를 재생성한다. plate 스위치 홀·노치는 키캡 폭과 무관.
- 스탠드오프 5 가정에서 스위치 핀 끝(plate 상면 아래 약 8.3 → Z 4.7)과 프레임 상면(3) 사이 여유는 1.7뿐이다. 배선·다이오드 높이(M14)에 따라 `TBD_standoff_H`가 커질 가능성이 높다.
- 커버 고정 방식(자석/나사/스냅)은 미정이다. 지금은 립으로 위치만 잡는다.
- 스위치 홀 46개는 r2 P3(16.5 개구) 중심·회전각을 썼다(P2 14mm는 45개만 사각형으로 인식됨, 차이 ≤0.2). SK20의 매개변수 템플릿 홀 2개(269.08, 82.01 / 62.96)는 실제 키 위치와 일치한다.

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
3. 확인: 스케치 12개 모두 `dof 0`, 타임라인 오류 0. `TBD_pcb0_dx/dy`가 바뀌면 고정 숫자 DXF 4종을 다시 만들어 스케치를 교체한다(삭제 → `sketch.create` + `sketch.insert_dxf` + 전체 `sketch.constraint.fix` → 컷 재생성): `python -I ../tools/make_key_dxf.py sq 14 <dx> <dy> REF_r2_keys_sq14_gh60.dxf`(SK22), `… sq 16.5 … REF_r2_keys_sq16p5_gh60.dxf`(SK24·SK25 공용), `python -I ../tools/make_r2_cover_dxf.py REF_r2_cover_windows_P4_gh60.dxf <dx> <dy>`(SK34). `jigs/`의 같은 이름 매개변수도 함께 바꾼다. 외곽은 `sketch.export_dxf`로 내보내 기대 좌표와 비교한다(검사 때 쓴 방식). 하우징 대용 바디는 부피와 `body_topology {"faces":"cylinders"}`의 기둥 중심으로 확인한다.
4. 저장한 뒤 `parameters.csv`와 `.sc`의 값이 같은지 대조하고 함께 커밋한다.

### 4. 다음 단계로 넘어가는 조건

**표의 실측이 끝나고 그 부품에 쓰이는 `TBD_`·`CAND_` 매개변수가 하나도 남지 않았을 때만** 부품 솔리드·STL을 만든다. Wilmore 대용값(`REF_WIL_`)을 참조하는 `TBD_`도 미확정으로 센다. 하우징 대용 바디는 어느 단계에서도 출력하지 않는다.

| 단계 | 필요한 실측 | 만들 것 |
|---|---|---|
| A. 체결 시험 프레임 | M01, M02, M03, M07, M08, M09, M10 (+M18 공정) | 얇은 판(2.5 mm) 시험 출력. 6개 나사가 억지 없이 들어가는지 확인 (planning.md §4). 형상은 `jigs/46es_jig_A_case_holes.sc`에 있고 실측값 반영 후 STL |
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
