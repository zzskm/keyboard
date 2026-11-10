# 46es 3D 모델 — 현행 안내

현행 **v5**. 편집 원본(SOT): [`../tools/build_seam_v5.py`](../tools/build_seam_v5.py). 생성 CAD [`46es_mount_seam_v5.sc`](46es_mount_seam_v5.sc)는 직접 편집 금지(생성기→재생성→검토/출력→검증→가이드). ([AGENTS.md](../AGENTS.md) §4, [design](../docs/design.md))

## 현재 파일

| 구분 | 경로 | 역할 |
|---|---|---|
| 편집 원본 | [`../tools/build_seam_v5.py`](../tools/build_seam_v5.py), [`../tools/mounts_v5.py`](../tools/mounts_v5.py) | v5 생성 규칙. mount는 도면 돌출 + 매개변수 체결부 |
| mount 도면 | [`mounts_cadcraft_phase1.dxf`](mounts_cadcraft_phase1.dxf) | CADCraft 평면 원본: 외곽·받침·Rear shim은 생성 입력, 홀·머리 자리 레이어는 검사 대상, `*_RELIEFS`는 참고 |
| 현행 CAD | [`46es_mount_seam_v5.sc`](46es_mount_seam_v5.sc) | 생성 결과 |
| 매개변수 | [`parameters_seam_v5.csv`](parameters_seam_v5.csv) | CAD 내보내기(독립 원본 아님) |
| 조립 검토 | [`46es_assembly_review_v5.sc`](46es_assembly_review_v5.sc), [`assembly_reference_v5.json`](assembly_reference_v5.json) | 파생/검토용. 실물·주문용 아님 |
| 제작 세트 | [`print_v5/`](print_v5/) | 주문 1 시험 → 주문 2 본 출력 |
| 검토 출력 | [`review_v5/`](review_v5/) | 조립 좌표 검토. `print_v5` 대체 불가 |
| 시험 쿠폰 원본 | [`samples/`](samples/) | B 쿠폰/보스 탭 입력 |
| 회귀 기준 | [`baselines/`](baselines/) | 고정 기준(SOT 아님) |
| 실측 | [`measurements/`](measurements/), [`measurements.csv`](measurements.csv) | CSV=상태/채택, JSON=원본 관찰 |

## 재생성·검증

CAD 재생성/검증은 [`../docs/validation.md`](../docs/validation.md). CAD 없는 정적 검사:

```sh
python -B 46es/tools/check_repository.py
```

## 보존된 원본과 참고 모델

삭제/이동 전 코드·문서·검사 의존성 확인.

| 항목 | 상태 |
|---|---|
| `measure_psd60.html` | 실측 입력 시트. 내보낸 JSON은 `measurements/`에 원본으로 두고 채택 판단은 `measurements.csv`에 적는다 |
| `reference_r2/` | DWG/r2 비교 참고 |

split v1, minimal v2, side-pairs v3의 모델·검토 출력·설계 보고·검증 로그는 Git 커밋 `7744368`의 `46es/`에서 찾을 수 있다. 예를 들어 저장소 루트에서 `git ls-tree -r --name-only 7744368 -- 46es/model 46es/docs 46es/inspection`으로 목록을 확인한다. v4·v5 두 단 커버 문서, `print_v4`, `guide_v4.json`은 태그 `46es-pre-cleanup-2026-11-06`(= `72d3ea1`)에 있다. 초기 스케치 모델(`46es_draft_sketches.sc`·`parameters.csv`), 지그 A(`jigs/`), 2026-11-04 조립 여유 렌더, 옛 B 쿠폰 STL/STEP은 태그 `46es-pre-cleanup-2026-11-09`에 있다.

현재 판단 기준: [`../README.md`](../README.md), [`../docs/design.md`](../docs/design.md), [`../docs/validation.md`](../docs/validation.md), [`print_v5/README.md`](print_v5/README.md).
