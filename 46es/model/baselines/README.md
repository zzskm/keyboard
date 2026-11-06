# 현행 생성·검증 기준 (비-SOT: 회귀 검증용)

| 파일 | 필요한 이유 |
|---|---|
| [seam_v4.sc](seam_v4.sc) | `tools/build_seam_v5.py`가 읽는 입력. `verify_seam_v5.py`가 미변경 바디를 비교한다 |
| [flat_Z18.sc](flat_Z18.sc) | `verify_seam_v5.py`가 plate 불변·커버 부피 차이를 검사하는 v5 초기 평판 기준 |

이 폴더의 파일들은 **회귀 검증용 기준**이지 **Source of Truth(SOT)**가 아니다. SOT는 `tools/build_seam_v5.py`다. 두 파일은 정리 전 커밋에서 경로만 바꿨으며 내용은 같다. 비교 기준의 해시는 검증 코드에 고정되어 있다. 과거 설계 모음이 아니며 두 파일 모두 주문용이 아니다. 원본 경로·과거 설명은 [정리 전 커밋](https://github.com/zzskm/keyboard/tree/72d3ea1ea8939ef29bc34afd62b5b2a4978f19a6/46es/model)에 있다.
