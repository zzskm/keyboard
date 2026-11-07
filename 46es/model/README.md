# 46es 3D 모델 — 현행 안내

현행 **v5**. 편집 원본(SOT): [`../tools/build_seam_v5.py`](../tools/build_seam_v5.py). 생성 CAD [`46es_mount_seam_v5.sc`](46es_mount_seam_v5.sc)는 직접 편집 금지(생성기→재생성→검토/출력→검증→가이드). ([AGENTS.md](../AGENTS.md) §4, [design](../docs/design.md))

## 현재 파일

| 구분 | 경로 | 역할 |
|---|---|---|
| 편집 원본 | [`../tools/build_seam_v5.py`](../tools/build_seam_v5.py) | v5 생성 규칙 |
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
python -I 46es/tools/update_manifest.py --check
```

## 보존된 과거/참고 변형 (현행 제작 경로 아님)

삭제/이동 전 코드·문서·검사 의존성 확인.

| 항목 | 상태 |
|---|---|
| `46es_draft_sketches.sc`, `parameters.csv`, `measure_psd60.html`, `jigs/` | 초기 스케치/측정/지그 기록 |
| `46es_mount_split_v1*`, `review_split_v1/`, `../scripts/split_v1*`, `../inspection/scripts/verify_split_v1.py` | split v1 실험/검토 |
| `46es_mount_minimal_v2*`, `review_minimal_v2/`, `../inspection/scripts/verify_minimal_v2.py` | minimal v2 실험/검토 |
| `46es_mount_side_pairs_v3*`, `review_side_pairs_v3/`, `../inspection/scripts/verify_side_pairs_v3.py` | side-pairs v3 실험/검토 |
| `46es_mount_tolerance*`, `46es_assembly_tolerance*` | 2026-11-04 조립 여유 검토 |
| `reference_r2/` | DWG/r2 비교 참고 |

현재 판단 기준: [`../README.md`](../README.md), [`../docs/design.md`](../docs/design.md), [`../docs/validation.md`](../docs/validation.md), [`print_v5/README.md`](print_v5/README.md).
