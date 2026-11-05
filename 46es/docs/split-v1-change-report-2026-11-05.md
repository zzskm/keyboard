# 46es split mount·plate 변경 및 검증 보고서

기준일: 2026-11-05 KST. **검토 모델 / 제작 승인·발주 아님.**

저장 모델에서 이어서 수정했다. 원본을 재생성하거나 `scripts/split_v1.commands.json`을 변형 모델에 재실행하지 않았다.

## 결과 파일

- [변형 모델](../model/46es_mount_split_v1.sc), [별도 파라미터 CSV](../model/parameters_split_v1.csv): 사용자 파라미터185개.
- [검토용 STEP](../model/46es_mount_split_v1_REVIEW_ONLY.step), [부품별 검토용 STL 7개](../model/review_split_v1/README.md).
- [구매 후보와 체결 스택](split-v1-hardware-2026-11-05.md), [국부 시험 출력안](split-v1-local-print-plan-2026-11-05.md), [인계](handoff-split-v1-2026-11-05.md).
- [전체 조립 렌더](../model/46es_mount_split_v1_review_iso.png), [게이트 단면](../model/46es_split_v1_gate_section_review.png), [SO6 단면](../model/46es_split_v1_so6_section_review.png), [USB 우회 연결](../model/46es_split_v1_usb_bridge_review.png).

## 시작 상태와 보존

- 실제 Git 저장소 `E:/Work/keyboard`, main/fa7e588f8d4a302ec7f2817ab0eb26c510b34c1a. 인계와 동일한 staged33개(수정8/추가6/삭제19), 기존 tracked unstaged0개, untracked4개로 시작했다.
- SolidCraft는 빈 headless 세션, dirty=false. 저장 변형을 열었을 때121바디·335피처·44스케치 dof0·오류0이었다.
- 원본 `46es_draft_sketches.sc`는 이번 작업에서 쓰지 않았다. 시작/종료 SHA256 `e9c99ca1f38d741c7c0c6ae34efc56b172f9cb2bf38860c2bd277a28ba43b232`.
- 시작 변형 SHA256 `fc6ba4d6ecb1065e5fd66d06b5d9bc253d7ea1f27e0572135f02ae759cbb8b22`.
- 최종 변형 SHA256 `3ccfcea5cbddedf776c15c14f75efd3fe7eca30d2ff2f1ad769be1cda712681e`.
- 원본과 기존 staged 변경을 보존했다. reset/checkout/기존 변경 삭제 없이 진행했다. 마지막 사용자 문장의 **all local changes commit/push 요청**을 앞선 금지보다 우선 적용한다. 저장 시 SolidCraft 자동 `.bak`도 보존한다.

## 1. 왼쪽 mount의 실제 단절 수정

closed=true만으로 한 조각이라고 판단하지 않았다. 저장 SCBREP04 캐시를 읽기 전용 분석했다.

| 초기 shell | 범위 X / Y / Z mm | 부피 mm³ |
|---|---|---:|
| 뒤쪽 띠 | 25.713–110 / 84.967–94.967 / −3–3 | 약2371.672 |
| 왼쪽·앞쪽 프레임 | −0.393–110 / −0.367–94.967 / −3–3 | 약5614.613 |

수평 면의 z·n_z 적분으로 얻은 합7986.28485는 SolidCraft7986.29349와0.00864mm³ 차이다. 곡선을 샘플링한 근사값이며, 두 shell은 서로 떨어진 양의 실체다. 내부 폐공간이 아니다. USB 노치가 뒤 rail을 끊고 중앙 분할이 원래 프레임의 우회 연결을 제거했다.

USB 노치 전체(X11.713–25.713, Y79.967 이후)를 보존하고 그 앞쪽으로 폭4mm U 우회 연결을 추가했다. 가로 X5.607–29.713/Y75.967–79.967, 우측 다리 X25.713–29.713/Y79.967–88.967, Z0–3이다. 기존 왼쪽 rail·뒤 rail과 각각2mm 중첩한다.

예상 추가349.272mm³, 실제349.271999998mm³로 일치했다. shells2→1. M3 변경 전 부피8335.565489mm³. USB 점유·plate·SO2와 간섭/미검사0. 스위치 가정 핀 하단Z4.7까지1.7mm이며 실제 배선 점유는 아직 입력되지 않았다.

## 2. M3 체결 후보 적용

Harwin M3 암–암 관통 지지대 길이6/AF5 후보를 적용했다. 포켓 AF5.4/깊이1, 지지대 Z2–8. Plate 하면Z8과 기존 키 높이를 유지한다. 컨트롤러 Y는13.064485로 고정하여 AF에 종속되지 않게 했다.

위쪽 M3×4와 아래쪽 M3×5 참조를 반영했고 머리는 보수적인 원통 포락 Ø5.7/H1.65다. 공칭 물림은2.5/3mm, 끝 간격0.5mm. 실제 챔퍼·나사산·길이 공차에 따른 유효 물림과 끝 간격은 현물 확인 전이다.

- Mount 포켓 바닥 잔여 두께2mm, SO6 포켓↔컨트롤러 개구 사이 살1.744485mm.
- SO3 회피Ø6.8와 AF5 육각 꼭짓점 외경5.773503 사이 최소 공칭 반경 여유0.513249mm.
- Plate 카운터보어Ø6 대비 머리Ø5.7의 반경 여유0.15mm. 머리 상단Z11.15 / 자석 하단Z11.6 사이0.45mm.
- SO3·SO6 주변15바디 검사에서 간섭0·미검사0. Cover 보스·자석 포켓은 수정하지 않았다.

## 3. M2와 컨트롤러 게이트

NBK SSH 저두 M2×6(plate/spine6개), M2×5(mount lap4개+gate1개), AF4/H1.6 금속 너트11개 후보로 정리했다. 비표준 M2×3.5와0.2T 와셔 가정을 없애고 와셔 참조10개와 해당 bore 피처를 억제했다. 나사 머리는Ø4/H1.1 포락이다.

- Plate M2 머리 바닥Z10.2, ×6 끝Z4.2. 남는 plate 두께는 브래킷 위치2.2mm, spine seat 위치1.7mm다. Nut 포켓은 AF4.4/깊이1.8.
- 컨트롤러 고정 보스2개를6×6에서8×8로 확장: 중심(125,17)/(125,25) 유지, 육각 꼭짓점 옆 살1.459659mm 이상. 18.5mm 스위치 보호 정사각형과 최소2D 거리1.616463mm.
- Gate 볼트 중심은(116.5,7.764485), 종전보다Y−0.75. PCB·플러그는 이동하지 않았다.
- Ear는 X113.5–120.5/Y4.264485–11.264485/Z4.8–6.4. Gate cap은 X112.581–120.5/같은Y/Z6.4–9.6. 서로Z6.4에서 접촉한다.
- Gate nut 포켓 바닥Z7.8/깊이1.8, 아래 받침1.4mm. 최소 옆 살1.3mm. 금속 너트Z7.8–9.4, 볼트 끝Z9.8로 너트 아래쪽에서1.6mm 전체 높이를 통과하고 위로0.4mm 나온다.
- Gate 머리Z3.7–4.8와 mount 상면Z3 사이0.7mm. Plate 회피 포켓 천장Z10, cap 위0.4/볼트 끝 위0.2mm, plate 위 잔여3mm.
- Plate 모듈을 케이스에서 꺼낸 상태에서 아래쪽으로 접근한다. Ø3 공구 포락 Z−8–3.7을 임시 생성해 모듈과 간섭/미검사0을 확인한 뒤 checkpoint로 완전히 복원했다. 실제 드라이버/조립 손동작은 별도 시험한다.

Gate 최초 포켓 확대 제거량107.4642mm³와 이후 확대30.857mm³가 계산값과 일치했다. Gate 확장46.8112mm³도 일치했다. Bracket 확대는 boss 증가117.6 + ear 증가26.3128 − 기존 위 lip과 중첩3.05794 =140.85486mm³로 실제와 일치한다.

고정 스케치를 이동하려던 batch는 `fixed or projected geometry cannot move`로 전체 롤백됐다. 이후 스케치 평면을Y−0.75로 이동해 적용했다. 실패 batch를 적용된 변경으로 세지 않았다. Rear head 입력1건을 확인해 올바른 offset d485에 적용하고 extent d486은 원래2.6으로 복원했다.

## 4. 최종 형상과 검증

| 출력 바디 | X 길이 mm | 부피 mm³ | shell / STL 성분 |
|---|---:|---:|---:|
| PLATE_L_SPLIT_V1 | 137.024 | 38045.573775 | 1 / 1 |
| PLATE_R_SPLIT_V1 | 154.257 | 40776.595123 | 1 / 1 |
| MOUNT_L_SPLIT_V1 | 110.393 | 8343.558135 | 1 / 1 |
| MOUNT_R_SPLIT_V1 | 195.188 | 14548.355567 | 1 / 1 |
| PLATE_SPINE_V1 | 30.000 | 1766.322263 | 1 / 1 |
| CTRL_BRACKET_SPLIT_V1 | 35.681 | 1415.593216 | 1 / 1 |
| CTRL_GATE_SPLIT_V1 | 7.919 | 186.473948 | 1 / 1 |

- **111바디·339피처·44스케치 전부 dof0·오류0·저장 dirty=false.** 경고1개는 원본 HOUSING_POSTS_CAND의 Boolean 미세 이동이다.
- 3D XY 외곽285.781×95.334 유지. 각 출력 부품 X≤250. Plate2분할, mount2분할, 별도 spine. SO3·SO6는 왼쪽 plate에 유지.
- SK22/SK24/SK25/SK34의 저장 입력 JSON은 원본과 모두 동일. 46키 XY/각도와1.5T 체결층 보존. 새 plate join은 없고, 넓힌 bracket 보스도 스위치 보호 영역 밖이다. Mount 우회 join은Z0–3이다.
- H02 인근 받침의 상면Z3.95↔spine 하면Z4 틈0.05와 shim 조정 방침 유지. H05 조정 장공·약2.002mm 잔여 살 유지.
- 새 파라미터 조합(USB bridge3.8, gate cap H3.1, support gap0.1) 시험: 오류0, parameter error0, 왼쪽 mount/gate shell1, restored=true. 시험값을 제작 허용 범위로 승인한 것은 아니다.
- STL7개 모두 경계 edge 사용2회, 비정상 edge0, 연결 성분1. CAD 대비 STL 부피 최대 차0.0212%, bbox 차0.05mm 이내. 검사 quantization은0.0001mm다. 일반적인 모든 self-intersection을 증명하는 검사는 아니다.

### 전체 간섭의 정확한 판정

111바디의6105쌍 중 bbox 후보399쌍. 최초20초 검사에서38쌍이 남았고, 작은 묶음·개별 쌍으로 재검사했다. 최종 미평가 쌍은 없다. 실제 출력 부품/금속 하드웨어/가정 스위치 점유 사이 의도하지 않은 중첩0이다.

단, **전체 모델의 엄밀한 중첩0은 아니다.** 대용 하우징과 가정 케이스 M2 H02/H03 두 쌍에 각각0.002855706mm³ 중첩이 있다. 원본 Boolean 미세 이동으로 Ø2 보어 축이 약0.00048mm 이동·약1.7e−6rad 기울었고, 공칭Ø2 나사 참조와 얇은 초승달 겹침이 생긴다. `inspect.interference`는 이2쌍을 facets 불일치로 미검증 처리했으나, `inspect.clearance(min_volume=1e-6)`가 두 부피를 평가했고 unchecked=[]다. **참조 모델의 수치 접촉 문제**로 구분해 유지했다. PSD60 실부품 적합성으로 해석하지 않는다.

근거: [최종 간섭 감사](../inspection/data/split-v1-interference-final-audit.json), [정밀 clearance](../inspection/data/split-v1-housingStrictClearance.json), [원통 축](../inspection/data/split-v1-cylinders-final.json), [STL 검사](../inspection/data/split-v1-stl-validation.json).

## 미확정 사항과 제작 보류

실제 배선·다이오드·납땜, 핀/걸쇠 세부 형상, 키캡 전 스트로크, 탈착 동작과 USB 케이블 굽힘은 미검증이다. REF_SW_ASSUMED46개는 단순 점유 가정이며 Gateron 실부품 CAD 검증 결과가 아니다. 실제 PCB/USB 변형과 케이스 나사 규격·유효 깊이도 미확정이다. M1.6×14를 케이스 나사로 지정하지 않았다.

공칭0.15–0.7mm 여유가 FDM 출력 공차를 흡수한다고 보장하지 않는다. FDM 재료는 미정, JLC3DP 우선 견적 검토이며 출력 시험 후 fit/강성/체결 토크를 정한다. 전체 케이스 jig를 선행 조건으로 요구하지 않는다. 배선8mm를 이유로 키 높이를 올리지 않았다.

이번 세션의 정식 MCP export는 허용되어 **REVIEW_ONLY** STEP/STL을 생성했다. 이전 자동 승인 차단을 우회하지 않았다. 제작용 파일·최종 제작 승인·발주는 없다.

## 다시 확인하기

`python -B 46es/inspection/scripts/verify_split_v1.py` — 원본 해시, 키 배열4종, CSV185행,7부품 shell/폭/bbox/부피/STL 연결성 확인.

초기 재현 명령은 `scripts/split_v1.commands.json`, 이번 단계별 호출/결과는 `inspection/data/split-v1-*.json`에 있다. **현재 변형 모델에 일괄 재실행하지 않는다.**

## 갱신 기록

- 2026-11-05: 연결성·M3·M2/gate·참조 간섭·단면·STL 검토 및 별도 CSV 완료. 현물/제작 검증은 보류.
