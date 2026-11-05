# Split v1 review exports

기준일: 2026-11-05 KST. **REVIEW ONLY — 제작 승인·발주용 아님.**

정식 SolidCraft MCP export가 현재 권한에서 허용되어 생성했다. 이전 세션의 승인 차단을 우회한 파일이 아니다.

- 이 폴더의 STL7개는 출력 부품 각각의 검토용 mesh, 단위mm, 조립 좌표 유지.
- 상위 `46es_mount_split_v1_REVIEW_ONLY.step`은 같은7바디의 검토용 STEP 조립이다. 하우징/스위치 가정/하드웨어 참조/cover는 포함하지 않는다.
- `46es_mount_split_v1.sc`와 `parameters_split_v1.csv`가 편집 기준이다. STEP/STL은 파라메트릭 원본을 대체하지 않는다.
- 7개 모두 kernel shell1, STL 연결 성분1, 비정상 경계 모서리0. CAD 대비 STL 부피 오차 최대0.0212%. 모든 자체 교차나 실제 제조 적합성을 증명한 결과는 아니다.
- 배선·실제 부품·키캡 스트로크·재료/공정 공차·강도·체결 토크는 미확정이다. 제조용 파일은 제공하지 않았다.

상세: [변경 보고서](../../docs/split-v1-change-report-2026-11-05.md), [국부 시험안](../../docs/split-v1-local-print-plan-2026-11-05.md), [구매 후보](../../docs/split-v1-hardware-2026-11-05.md).
