# 현행 모델 — v5

| 파일 | 역할 | 편집·사용 기준 |
|---|---|---|
| [46es_mount_seam_v5.sc](46es_mount_seam_v5.sc) | 현행 설계 CAD | 생성기 결과. 자동 재생성 시 직접 편집은 덮어써진다 |
| [parameters_seam_v5.csv](parameters_seam_v5.csv) | 현행 CAD 매개변수 내보내기 | CAD와 일치해야 한다. 독립 원본으로 편집하지 않는다 |
| [46es_assembly_review_v5.sc](46es_assembly_review_v5.sc) | 케이스·키캡을 포함한 조립 검토 CAD | 출력하지 않는다. 생성기로 재생성 |
| [assembly_reference_v5.json](assembly_reference_v5.json) | 조립 검토 모델의 입력·출력 해시 | 생성기와 함께 갱신 |
| [print_v5/](print_v5/README.md) | 현행 시험·본 출력 세트 | 주문할 때 사용하는 유일한 폴더 |
| [review_v5/](review_v5/README.md) | 조립 좌표의 검토 출력물 | 주문용 STL과 방향이 다름 |
| [samples/](samples/README.md) | 스위치 홀·보스 시험 CAD | 행 C upper 1.7이 v5 plate를 재현 |
| [baselines/](baselines/README.md) | 생성·회귀 검증 기준 | 주문하거나 현행 모델로 편집하지 않는다 |

설계 변경은 `tools/build_seam_v5.py`의 생성 규칙에 반영한다. v4 기반 치수를 바꿔야 하면 기준 모델을 무조건 덮어쓰지 말고 생성기에 변경을 반영하고 검증 기대값을 검토한다. 내부 바디 이름 `PLATE_*_SPLIT_V1` 등은 현행 코드가 사용하는 식별자이며 폐기 여부 표시가 아니다.

[현재 설계](../docs/design.md), [검사·재생성 순서](../docs/validation.md), [실측 입력](measurements/README.md)을 따른다.
