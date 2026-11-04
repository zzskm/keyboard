# 46es 시험 지그 — A 단계 케이스 체결 시험판

상태: 형상만 작성 (2026-11-04). **STL 미생성.** `model/README.md` §4 A 단계(M01·M02·M03·M07·M08·M09·M10 실측) 뒤에 `TBD_`·`CAND_` 값을 실측값으로 바꾼 다음 내보낸다.

## 목적

PSD60 안에 얇은 판 한 장을 넣어 (1) 외곽·코너 모따기가 내벽에 들어가는지, (2) GH60 후보 좌표의 나사 구멍 6개가 하우징 기둥과 맞는지, (3) M2 나사가 억지 없이 들어가는지를 본다. 통과하면 같은 값으로 프레임을 만든다.

## 파일

| 파일 | 내용 |
|---|---|
| `46es_jig_A_case_holes.sc` | SolidCraft 디자인. 매개변수 21개(아래), 피처 10개, 바디 `JIG_A_CASE_HOLES_TBD` 1개 |
| `46es_jig_A_case_holes_top.png` | 위에서 본 렌더 |

## 형상

- 외곽: 하우징 내측(`TBD_case_in_W/D`) − 간격 `TBD_frame_gap`×2, 코너 모따기 `TBD_frame_C`, 두께 `JIG_T` 2.5.
- 구멍: `CAND_H01`–`H06`, Ø `TBD_case_screw_D + TBD_case_screw_clr`(2.4).
- 창 2개(재료 절약·기둥 육안 확인): 왼쪽 x 35–115 × y 15–80, 오른쪽 x 140–245 × y 20–80 (GH60 기준점 좌표, 고정 숫자). 구멍에서 6 이상 떨어져 있다.
- 부피 39,248.8 mm³(계산 39,248.8), bbox −0.393…285.388 × −0.367…94.967 × 0…2.5.

## 매개변수

`46es_draft_sketches.sc`와 **같은 이름·같은 값의 복사본**이다(`TBD_case_in_W/D`, `TBD_pcb0_dx/dy`, `TBD_frame_gap/C`, `TBD_case_screw_D/clr`, `CAND_H01_X`…`CAND_H06_Y`) + `JIG_T`. SolidCraft 파일 사이에 매개변수가 공유되지 않으므로, 실측 후 `parameters.csv`를 고칠 때 이 파일의 같은 이름도 `parameters.change`로 함께 바꾼다.

## 출력 조건 (실측 후)

JLC3DP FDM 최소 부품 크기 30×30×10 규칙에 2.5T 판이 걸리는지 업체에 확인한다(걸리면 창을 없애고 두께 3으로). 출력 방향은 평면을 베드에.
