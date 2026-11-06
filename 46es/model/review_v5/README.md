# v5 검토 파일 — 주문용 아님 (2026-11-06, 2차 두 단 커버)

[46es_mount_seam_v5.sc](../46es_mount_seam_v5.sc)에서 바뀐 부품만 **조립 좌표 그대로** 내보냈다. 출력 방향 회전이나 주문 폴더 분리는 하지 않았다. v5를 승인하면 [print_v4](../print_v4/README.md)처럼 주문 세트를 다시 만든다. 지금 주문 파일은 v4다.

| 파일 | 바디 | 재료(예정) | 부피 cm³ (1차 평판 Z 18 / v4) | 최소 벽 |
|---|---|---|---:|---:|
| `46es_v5_cover_L_REVIEW_ONLY` | COVER_L_DRAFT_TBD | 8001 레진 투명 | 9.29 (13.07 / 5.78) | 1.000 (다리 자석 포켓 위 살) |
| `46es_v5_cover_T_REVIEW_ONLY` | COVER_T_DRAFT_TBD | 8001 레진 투명 | 8.65 (12.06 / 5.21) | 1.098 (보스 둘레) |
| `46es_v5_cover_R_REVIEW_ONLY` | COVER_R_DRAFT_TBD | 8001 레진 투명 | 10.16 (13.61 / 6.17) | 1.000 (다리 자석 포켓 위 살) |
| `46es_v5_plate_L_REVIEW_ONLY` | PLATE_L_SPLIT_V1 | MJF PA12S-HP 검정 | 38.12 (38.12 / 38.12) | 1.000 |
| `46es_v5_plate_R_REVIEW_ONLY` | PLATE_R_SPLIT_V1 | MJF PA12S-HP 검정 | 40.64 (40.64 / 40.64) | 1.047 |
| `46es_v5_changed_REVIEW_ONLY.step` | 위 5개 + 다리 자석 참고 4개 | — | — | — |
| `flat_Z18/` | 1차 평판 커버(윗면 Z 18, 테두리 +4) 모델 + 커버 STEP 3개 | — | 13.07 / 12.06 / 13.61 | 1.098 |

커버는 두 단이다: 바닥 윗면 Z 16.1(테두리 +2.1), 창 둘레 폭 1.5 턱 Z 19.0(+5.0). 2차에서 plate 파일은 바뀌지 않았다(STL/STEP sha 동일, `seam-v5-exports.json`의 `plate_files_unchanged_since_previous_export`). 각 부품은 `.stl`(fine)과 `.step` 두 가지다. STL은 연결 성분 1개이고 열린 모서리가 없다. CAD와 부피 차이는 0.004 % 이하다. 커버 얇은 벽 검사에서 1.0 미만으로 잡힌 곳은 창이 가장자리와 만나는 모서리 끝과 회전 키 턱이 외곽과 비스듬히 만나는 쐐기 끝뿐이다(`wall_min_mm` ≥ 1.0). 해시와 얇은 벽 검사 결과는 `inspection/data/seam-v5-exports.json`, `seam-v5-thin-wall.json`에 있다. 변경 내용은 [v5 문서](../../docs/v5-cover-magnet-margin-2026-11-06.md)를 본다. 다시 만들려면 `python tools/export_seam_v5_review.py`를 실행한다.
