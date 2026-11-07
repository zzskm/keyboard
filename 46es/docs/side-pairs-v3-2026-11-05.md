> **역사 문서(현행 v5 기준 아님).** 이 문서는 작성 당시의 계획/실험/검토 기록이다. 현재 설계·제작·검증 판단은 [README](../README.md), [설계](design.md), [검증과 다음 작업](validation.md), [v5 제작 세트](../model/print_v5/README.md)를 우선한다. 필요한 결정/근거만 현행 문서로 옮긴다.

# 46es mount v3 — 좌우 부품 각각 병합

기준일: 2026-11-05 KST. 검토 모델, 제작 승인·발주 아님.

사용자 요청대로 왼쪽 앞/뒤2개를1개, 오른쪽 앞/뒤2개를1개로 합쳤다. 중앙 H02–SO3와 H03–SO6는 그대로다. **Mount6→4개, 전체 출력11→9개**다. 저장된 minimal v2에서 이어서 수정했고 원본/v1/v2는 보존했다.

## 최신 파일

- [v3 모델](../model/46es_mount_side_pairs_v3.sc), [CSV187행](../model/parameters_side_pairs_v3.csv), [검토 STEP](../model/46es_mount_side_pairs_v3_REVIEW_ONLY.step), [검토 STL9개](../model/review_side_pairs_v3/README.md).
- [Mount 상면](../model/46es_mount_side_pairs_v3_top_review.png), [plate 아랫면 체결 모습](../model/46es_mount_side_pairs_v3_underside_review.png).
- 시작 Git main/cb347054e40901297bb04be81ff4cede45c59648, clean. SolidCraft v2 dirty=false 확인 후 별도 v3로 저장했다.
- 원본 SHA256 e9c99ca1f38d741c7c0c6ae34efc56b172f9cb2bf38860c2bd277a28ba43b232, v1 3ccfcea5cbddedf776c15c14f75efd3fe7eca30d2ff2f1ad769be1cda712681e, v2 299517072bfc4f0328225dccab76dec0515674e09dba6a22020ad86670b5374d 보존.
- v3 SHA256 `04538a672f0160896743c1e6d94a44cd301591da00abbb18146be4245bd8d4b0`.

## 병합 구성과 부피

| 부품 | 포함 체결점 | X×Y mm | 부피 mm³ |
|---|---|---:|---:|
| MOUNT_L_PAIR_V3 | H05/H01 + SO1/SO2 | 30.592×91.825 | 2563.901389 |
| MOUNT_R_PAIR_V3 | H06/H04 + SO5/SO4 | 40.168×92.887 | 2337.117636 |
| MOUNT_H02_SO3_MIN_V2 | H02 + SO3, 중앙 받침 | 12.881×50.745 | 1409.168239 |
| MOUNT_H03_SO6_MIN_V2 | H03 + SO6, controller 앞쪽 | 69.818×13.079 | 1616.092569 |

케이스 체결점 H05↔H01, H06↔H04 사이에 **폭8×두께3mm** 연결 web을 추가하고 실제 겹치는 체적으로 union했다. 두 케이스 축에서 각각3.7mm 물러난 곳부터 연결하므로 기존 구멍/머리 자리의 최대 반경3.2mm와 최소0.5mm를 분리한다. 외곽을 다시 두르는 링은 만들지 않았다. 추가 볼트/너트는 없다.

왼쪽 원2부품 합1924.426690→2563.901389, 오른쪽1695.939687→2337.117636mm³. Mount 합6645.627186→7926.279833mm³로 증가했지만 초기 둘레 프레임22891.913702보다 **65.3752% 적다**.

독립 계산은 새 사각 연결부 체적에서 저장 v2 밑면과의 겹침을 빼는 방법이다. 곡선4096분할·wire endpoint 정렬 후 예측2563.906509/2337.127953, CAD와의 차−0.005119/−0.010317mm³로 일치한다. 임시 원래 위치의 연결부와 기존 각 부품 간 exact 간섭 부피도 별도로 확인하고 checkpoint를 복원했다. 처음의 정렬하지 않은 loop 면적 예측은 폐기했다.

## 보존·검증

- **105바디·401피처·60스케치 모두 dof0·오류0·dirty=false**. 경고는 원본 HOUSING_POSTS_CAND1개다.
- 좌/우 병합 부품 각각 native shell1. 전체 출력9개가 모두 shell1·STL 연결 성분1·비정상 경계 edge0. CAD 대비 mesh 부피 최대 차0.0289%, bbox 차0.05mm 이내. 일반 자체 교차 전체 증명은 아니다.
- v2와 공통으로 남은 **103바디 exact BRep 동일**. Plate/중앙 mount2개/spine/브래킷·게이트/지지대/cover·자석 등은 유지됐다. SK22/SK24/SK25/SK34 원본 입력 동일. 외곽285.781×95.334,46키 위치·각도·높이 유지.
- M3 구멍Ø3.4·육각 포켓AF5.4/깊이1/바닥2mm, 기존 case 장공Ø2.4·머리 자리Ø4.4 및 H05 조정±0.9/잔여 살 약2.00234mm를 토폴로지로 확인했다. 새 web은Z0–3이며 plate 릴리프·1.5T 체결층을 메우지 않는다.
- USB 가정 점유와 왼쪽 부품 사이 최소1.0189999mm 유지, controller/gate/USB와 겹침0. H02 shim 받침과0.05mm 간격은 공통 BRep 그대로다.
- 변경된2바디↔나머지103바디의206쌍 중191쌍 bbox 제외/15쌍 평가, 미검사0·겹침0(`min_volume=1e-6`). 새 좌우끼리1쌍도 검사 완료. 총207개 변경 관련 쌍이 평가됐다. 받침/볼트 머리 접촉은 정상 접촉으로 분리했다.
- 나머지103바디 간5253쌍은 exact BRep 동일성을 근거로 v2 검사를 승계한다. 대용 하우징↔가정 나사 H02/H03/H06의 기존 약0.00285mm³ 수치 중첩3쌍은 그대로며 엄밀한 전체 중첩0으로 쓰지 않는다. 실부품 CAD 검증이 아니다.
- 새 파라미터 `side_pair_bridge_W`=8, `side_pair_bridge_end_setback`=3.7. 조합7.5/3.8과8.5/3.6 시험 모두 오류0·단일 shell·restored=true. 시험 범위를 제조 허용 공차로 승인한 것은 아니다. 기존 v2 mask/web 고정 좌표 제한은 유지된다.

근거 `inspection/data/side-pairs-v3-*.json`, 재검사 `python -B 46es/inspection/scripts/verify_side_pairs_v3.py`.

## 조립·국부 시험과 미확정 사항

좌우 각각2개 케이스 포스트에 걸리므로 두 나사를 느슨하게 시작해 장공 위치를 맞춘 뒤 조인다. Plate를 임시 장착해 SO1/SO2, SO4/SO5가 힘 없이 맞는지 확인한다. 접근이 막히면 plate를 들어내고 케이스 나사를 최종 조인다. 전체 케이스 jig는 선행 조건이 아니다.

새 연결부 양 끝의 융합·층간 강도, 두 케이스 홀의 실제 간격/높이와 장공 조정 끝, 반복 탈착 후 들뜸을 국부 시험한다. v2의 긴 중앙 앞쪽 어댑터와 H02 shim 시험도 유지한다. M3 6mm 지지대/위×4/아래×5, M2 plate·spine×6/게이트×5 및 너트7개 구매 후보는 그대로다.

실제 배선·납땜·다이오드·키캡 전 스트로크, 케이스 나사 규격/깊이, 소재·층방향·강성/creep는 미확정이다. 키 높이를 올리지 않았다. JLC3DP 우선 검토·FDM 소재 미정, 제작용 내보내기·승인·발주 없음. STEP/STL은 모두 REVIEW_ONLY다.

## 갱신 기록

- 2026-11-05: minimal v2의 좌우 각2개를 연결·병합,4 mount/9출력 부품 검증 및 검토 내보내기.
