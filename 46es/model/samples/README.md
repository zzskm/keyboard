# 46es 출력 샘플 — B 단계 스위치 홀 쿠폰

상태: 설계 완료, STL/STEP 내보냄, **미발주** (2026-11-04, 사용자 승인 후 내보냄). `model/README.md` §4의 B 단계(스위치 홀 샘플) 시험물이다. 이 쿠폰은 시험용이며 46es 부품이 아니다.

## 근거가 된 결정 (2026-11-04)

| 항목 | 결정 | 출처 |
|---|---|---|
| M11 기존 아크릴 홀 | 실측 생략, r2 DWG 14.0 출발값 | 사용자(레이저 커프와 FDM 공차는 별개) |
| M18 공정 | FDM, 업체 후보 JLCPCB(JLC3DP), 재료 미정 | 사용자 |
| M19 스위치 | Gateron KS-3 Milky Yellow (Pro), 5핀 PCB 마운트형, MX 호환 | 사용자 |
| 스냅 홀 형상 참고 | 3×3 fidget(Printables 1077722): 홀 14.0, 남김 1.4, 노치 16×8×1.5 4변, "fit well" | `../../inspection/switch_tester/README.md` |

## 파일

| 파일 | 내용 |
|---|---|
| `46es_sw_hole_sample.sc` | SolidCraft 디자인. 매개변수 15개(`SMP_`), 피처 41개, 바디 `SW_HOLE_SAMPLE` 1개 |
| `46es_sw_hole_sample.stl` / `.step` | 출력용 내보내기(binary STL, STEP). STL은 삼각형·bbox·부피·닫힘을 검사했다 |
| `46es_sw_hole_sample_top.png` / `_bottom.png` | 렌더(위/아래) |

## 쿠폰 형상

145.35 × 50.1 × 10 mm 한 장. X 방향으로 7열(홀 13.7 → 14.3, 0.1 간격), Y 방향 2행. 원점 코너(홀 13.7, 행 A 쪽)에 3 mm 모따기가 있어 방향을 알 수 있다.

| 행 | 위치 | 구조 | 시험 목적 |
|---|---|---|---|
| **A** (모따기 쪽, y 작음) | y = 15.5 | 홀 h × h 관통 + 상면 1.5 아래에 걸쇠 노치(편측 1.0 → 폭 h+2, 길이 8, 높이 1.5, 4변) + 그 아래 h × h 우물 | fidget 방식 재현. 46es plate "5T + 국부 박육" 후보 |
| **B** (나사 구멍 쪽, y 큼) | y = 34.55 | 홀 h × h 관통 + 상면 1.5 아래 하면 전체 16.5 × 16.5 개방 | 걸쇠 위치 무관 비교군. 노치 없이도 되는지 확인 |
| +Y 여백 | y = 47.1, x = 20/40/60/80 | Ø2.0 / 2.2 / 2.4 / 2.6 관통 | M2 나사 여유·자가 탭 시험 (`TBD_case_screw_clr`, `TBD_so_clr`) |

두께 10은 JLC3DP FDM 최소 부품 크기(30×30×10) 때문이다. 스위치 끼움은 상면 1.5와 그 아래 1.5 노치만 관여하므로 plate 두께 5와 결과가 같다.

## 매개변수

| 이름 | 값 | 의미 |
|---|---|---|
| `SMP_pitch` | 19.05 | 셀 간격 |
| `SMP_hole_min`, `SMP_hole_step` | 13.7, 0.1 | 열 i 홀 = min + i·step |
| `SMP_ledge` | 1.5 | 걸쇠 남김(상면→노치/포켓) |
| `SMP_notch_L`, `SMP_notch_D`, `SMP_notch_H` | 8, 1.0, 1.5 | 행 A 노치 길이·깊이·높이 |
| `SMP_pocket` | 16.5 | 행 B 개방 포켓 한 변 |
| `SMP_T`, `SMP_margin` | 10, 6 | 두께, 여백 |
| `SMP_L`, `SMP_W` | 식 | 7·pitch+2·margin, 2·pitch+2·margin |
| `SMP_scr_min`, `SMP_scr_step` | 2.0, 0.2 | 나사 구멍 |

검증: 부피 40,291.57 mm³(계산 40,291.50), bbox 0…145.35 × 0…50.1 × 0…10, 바디 1. `check_parameters`로 `SMP_hole_min`·`SMP_ledge`·`SMP_notch_L`을 바꿔 재빌드해 모든 피처가 따라오는 것을 확인했다.

## 출력·시험 절차

1. ~~STL 내보내기 전 사용자 확인~~ → 2026-11-04 승인, 내보냄(§4 게이트: B 단계 입력 M11·M18·M19는 결정/지정으로 채워졌고, 걸쇠 치수는 쿠폰이 직접 시험한다).
2. 출력 방향: **상면(홀 쪽)을 베드에** 놓는다. 행 B 포켓은 위로 열려 지지대가 필요 없고, 행 A 노치는 1.0 돌출 × 8 길이의 작은 브리지만 생긴다. 반대로 놓으면 행 B 포켓 천장 16.5를 브리지해야 한다.
3. 스위치(Gateron Milky Yellow)를 각 홀에 끼워 기록: 삽입력(헐거움/적당/억지), 걸쇠가 걸리는지, 키캡 뽑을 때 스위치가 딸려 나오는지, 좌우 흔들림. 행 A와 B의 차이도 기록.
4. 나사 구멍 4개에 M2 나사를 넣어 통과/자가 탭 여부 기록.
5. 홀 실측(캘리퍼 내경조)으로 설계값 대비 편차를 구해 `measurements.csv` M18에 적고, `TBD_sw_hole`·`TBD_sw_ledge_T`·`TBD_sw_relief_W`를 정한다.

## 재현

`46es_sw_hole_sample.sc`를 SolidCraft MCP 폴더에 복사해 `open`. 처음부터 만들려면 `parameters.add` 15개 → `solid.box BASE` → 홀 14개(`solid.box cut`, 중심 식) → 행 A 노치 14개 → 행 B 포켓 7개 → 나사 구멍 4개(`solid.cylinder cut`) → `solid.chamfer [[0,0,5]] 3` → `save`. 한 `batch`로 57단계, 기대 부피 40,291.5.
