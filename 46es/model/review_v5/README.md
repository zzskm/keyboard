# v5 검토용 출력물

현행 v5의 커버 L/T/R와 plate L/R을 **조립 좌표**로 내보낸 STEP/STL이다. `46es_v5_changed_REVIEW_ONLY.step`은 변경 부품과 자석 참고 바디를 함께 담는다.

주문용 파일은 [print_v5](../print_v5/README.md)에 있다. 이 폴더의 STL은 출력 방향으로 회전한 주문 파일을 대신하지 않는다.

재생성: 저장소 루트에서 `python 46es/tools/export_seam_v5_review.py`. 매개변수 CSV와 `inspection/data/seam-v5-exports.json`, `seam-v5-thin-wall.json`도 갱신한다. 초기 평판 비교 기준은 [baselines](../baselines/README.md)에 있다.
