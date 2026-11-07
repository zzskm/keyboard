> **역사 문서(현행 v5 기준 아님).** 이 문서는 작성 당시의 계획/실험/검토 기록이다. 현재 설계·제작·검증 판단은 [README](../README.md), [설계](design.md), [검증과 다음 작업](validation.md), [v5 제작 세트](../model/print_v5/README.md)를 우선한다. 필요한 결정/근거만 현행 문서로 옮긴다.

# 46es split v1 continuation

기준일: 2026-11-05 KST. 검토 모델이며 제작 승인/발주 아님.

## 시작 상태

- Repository E:/Work/keyboard, main, fa7e588f8d4a302ec7f2817ab0eb26c510b34c1a.
- 기존 staged 33개/unstaged 0개/untracked 4개, 인계와 동일.
- Source SHA256 e9c99ca1f38d741c7c0c6ae34efc56b172f9cb2bf38860c2bd277a28ba43b232.
- Split SHA256 fc6ba4d6ecb1065e5fd66d06b5d9bc253d7ea1f27e0572135f02ae759cbb8b22.
- SolidCraft 빈 headless 세션, dirty=false에서 저장 변형 모델 열기. 121 bodies, 335 features, 44 sketches all dof0, errors0, inherited housing warning1.
- 사용자 마지막 문장의 all-local commit/push 요청은 앞선 commit/push 금지보다 우선함. 원본/기존 변경 보존, reset/checkout 금지 유지.

## Stage 1 — 왼쪽 mount 연결성

- 저장 SCBREP04 캐시를 읽기 전용으로 분석. Shell0: X25.713–110, Y84.967–94.967, Z−3–3, 약2371.672mm³. Shell1: X−0.393–110, Y−0.367–94.967, Z−3–3, 약5614.613mm³.
- 수평 면의 z·n_z 면적 적분(곡선 수치 샘플링) 합7986.28485와 SolidCraft7986.29349 차이0.00864mm³. 두 양의 실체가 USB_NOTCH(X11.713–25.713, Y79.967 이후)에 의해 단절. 내부 폐공간 아님. 중앙 분할로 기존 우회 연결이 사라짐.
- 원 USB notch 전체를 보존하는 안쪽 U 우회 연결 추가: 가로 X5.607–29.713/Y75.967–79.967, 우측 다리 X25.713–29.713/Y79.967–88.967, Z0–3. 최소 폭4mm, 기존 왼쪽 rail과 가로 연결의 중첩2mm, 뒤 rail과 다리 중첩2mm.
- 예상 추가349.272mm³; 실제349.271999998mm³. 새 부피8335.565489mm³. Kernel shells2→1, closed=true. 외곽/구멍/키 배열 미변경. 스위치 가정 핀 하단Z4.7까지 수직 여유1.7mm. 실제 배선 점유 미검증.
- 재현용 전체 초기 split 명령은 재실행하지 않음. 신규 명령만 별도 보관.

## Stage 2–4 — 최종 저장

- M3 6mm/AF5·포켓깊이1·위×4/아래×5 반영, controller Y 고정. M2 표준길이×6/×5 및 저두 머리, 와셔 참조 억제. Gate/보스 잔여 살 보강.
- 111바디/339피처/44스케치 dof0/오류0/원본 경고1/dirty=false.7출력 부품 shell1 및 검토 STL 연결1/비정상edge0.
- 전체 간섭 평가 후 대용 하우징↔가정 M2 H02/H03 수치 중첩 각각0.002855706mm³만 분리 기록. 미평가 쌍0.
- 현재 상세는 [최종 변경 보고서](split-v1-change-report-2026-11-05.md), [인계](handoff-split-v1-2026-11-05.md)를 따른다. 실제 부품·배선·키캡·재료 시험은 미완료, 제작 보류.
