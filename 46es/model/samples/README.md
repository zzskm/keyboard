# 46es 출력 샘플 — 스위치 홀 쿠폰(B)

상태: 설계/STL/STEP 완료, **미발주**(2026-11-04). 시험용 쿠폰(46es 부품 아님).

## 결정 근거 (2026-11-04)

| 항목 | 결정 |
|---|---|
| M11 홀 출발값 | r2 DWG 14.0 (레이저 커프 ≠ FDM) |
| M18/M19 | FDM 후보 JLC3DP, Gateron KS-3 Milky Yellow Pro(5핀, MX) |
| 형상 참고 | fidget 14.0/남김1.4/노치16×8×1.5, `../../inspection/switch_tester/README.md` |

## 파일

| 파일 | 내용 |
|---|---|
| `46es_sw_hole_sample.sc` | SolidCraft 원본(`SMP_*` 15개, `SW_HOLE_SAMPLE`) |
| `46es_sw_hole_sample.stl/.step` | 출력용(검사 완료) |
| `*_top.png`, `*_bottom.png` | 렌더 |

## 형상

145.35 × 50.1 × 10 mm. X 7열(홀 13.7→14.3, 0.1), Y 2행. 원점 코너(13.7, A) 3 mm 모따기=방향.

| 행/구멍 | 구조 | 목적 |
|---|---|---|
| A (y=15.5) | h×h 관통 + 상면 1.5 아래 노치(편측1.0, 16×8×1.5, 4변) + 우물 | plate 5T+국부 박육 후보 |
| B (y=34.55) | h×h 관통 + 상면 1.5 아래 16.5×16.5 개방 | 노치 무관 비교 |
| +Y 여백 | Ø2.0/2.2/2.4/2.6 관통 | M2 여유/자가탭 |

두께 10은 FDM 최소(30×30×10). 스위치 끼움은 상면 1.5+노치 1.5만 관여.

## 주요 매개변수

`SMP_pitch` 19.05, `hole_min/step` 13.7/0.1, `ledge` 1.5, `notch L/D/H` 8/1.0/1.5, `pocket` 16.5, `T/margin` 10/6, `scr_min/step` 2.0/0.2. 검증: 40,291.57 mm³, bbox 0..145.35×0..50.1×0..10.

## 출력·시험

1. 출력 방향: **홀 쪽(상면) 아래/베드**. B 포켓 지지대 불필요, A 노치는 소형 브리지.
2. 각 홀에 Milky Yellow 삽입: 삽입력, 걸쇠, 뽑을 때 이탈, 흔들림, A/B 차이 기록.
3. M2 구멍 Ø2.0–2.6 통과/자가탭 기록.
4. 홀 내경 실측 → `measurements.csv` M18, `TBD_sw_hole`/`ledge_T`/`relief_W` 결정.

## 재현

SolidCraft에서 `46es_sw_hole_sample.sc` 열기. 새로 만들면 `SMP_*` 15개 → BASE box → 홀14/노치14/포켓7/나사4/cut → chamfer `[0,0,5] r3`(batch 57단계, 부피 ~40,291.5).
