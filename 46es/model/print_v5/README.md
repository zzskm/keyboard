# 46es v5 출력 세트 — 주문 2 (`order2/`)

기준일: 2026-11-06(3차 안전마진). 모델은 [`../46es_mount_seam_v5.sc`](../46es_mount_seam_v5.sc), 매개변수는 [`../parameters_seam_v5.csv`](../parameters_seam_v5.csv)다. 사용자 결정(2026-11-06): 아직 주문하지 않았으므로 **v5가 현행 설계**이고, 주문 2는 이 폴더의 파일로 넣는다. 설계 내용은 [v5 문서](../../docs/v5-cover-magnet-margin-2026-11-06.md), 재료·하드웨어·주문 메모·주문 1 도착 후 시험은 [print_v4/README.md](../print_v4/README.md)를 그대로 따른다(v4와 다른 점만 아래에 적었다).

**주문 1(시험 출력)은 [print_v4/order1](../print_v4/order1/)을 그대로 쓴다.** mount 4개, 이음 쿠폰 L·R, B 쿠폰(행 C upper 1.7 = v5 plate), 보스 탭은 v4와 v5에서 같은 바디다(`verify_seam_v5.py`가 미변경 58바디의 BRep 동일을 확인한다). 주문 1의 시험이 통과하면 주문 2를 넣는다. 주문 1의 mount가 맞지 않아 고쳤다면, 고친 mount를 주문 2에 넣는다.

## 주문 2 — 본 세트 (`order2/`)

| 파일 | 무엇 | 재료 | 수량 | STL 방향 (참고) | 크기 X×Y×Z mm | 부피 cm³ | 최소 벽 |
|---|---|---|---:|---|---|---:|---:|
| `46es_v5_plate_L` | plate 왼쪽 반 (앞 이음 tab, upper 1.7, 다리 자석 포켓 Ø3.3 + 앞 단차 받침) | MJF 검정 | 1 | 윗면이 아래 | 143.29×95.33×8 | 38.1 | 1.00 |
| `46es_v5_plate_R` | plate 오른쪽 반 (앞 이음 포켓, upper 1.7, 다리 자석 포켓 + 받침) | MJF 검정 | 1 | 윗면이 아래 | 154.26×95.33×8 | 40.6 | 1.05 |
| `46es_v5_spine` | 이음부 아래 받침(배선 홈 3곳). **v4와 같은 바디** | MJF 검정 | 1 | 윗면이 아래 | 30×49×4.5 | 1.7 | 1.00 |
| `46es_v5_ctrl_bracket` | Pro Micro 브래킷. **v4와 같은 바디** | MJF 검정 | 1 | 지붕이 아래 | 35.68×28.60×7 | 1.4 | 1.00 |
| `46es_v5_ctrl_gate` | Pro Micro 빠짐 방지 게이트. **v4와 같은 바디** | MJF 검정 | 1 | 너트 포켓 면이 아래 | 7.92×11×7.6 | 0.2 | 1.30 |
| `46es_v5_cover_L` | 커버 왼쪽 (ㄷ형). 두 단(바닥 Z 16.4 / 창 둘레 턱 Z 19), 키캡 여유 1.0 창, 아래 다리 자석 포켓 Ø3.2 | **8001 투명** | 1 | 윗면이 아래(보스·턱이 위) | 101.79×95.33×7.5 | 9.9 | 1.10 |
| `46es_v5_cover_T` | 커버 가운데 (T형). 두 단 | **8001 투명** | 1 | 윗면이 아래 | 87.70×95.33×7.5 | 9.3 | 1.10 |
| `46es_v5_cover_R` | 커버 오른쪽 (ㄷ형). 두 단, 아래 다리 자석 포켓 | **8001 투명** | 1 | 윗면이 아래 | 128.70×95.33×7.5 | 10.8 | 1.10 |

v4 주문 2와 다른 점: plate는 upper 층 1.7(스위치 착좌 Z 11.3)과 앞 가장자리 다리 자석 포켓·받침, 커버는 두 단 7.5 높이(v4 3.5)와 넓어진 창(키캡 + 1.0), 다리 자석 포켓이다. spine·브래킷·게이트는 같은 바디를 한 폴더에 두려고 다시 내보냈을 뿐이다(부피·크기 v4와 동일).

- 커버 최소 벽 1.098은 보스 둘레다(8001 권장 0.8 초과). 다리 자석 포켓 위 살은 1.3(레진 벽 규칙 1.0 + 안전마진 0.3, 3차). 앞·뒤 좁은 베젤(1.16–1.4)은 창 여유 1.0(사용자 요구)과 케이스 내벽 사이라 더 넓힐 수 없다 — 출력 후 강도를 본다(v5 문서 「남은 실물 확인」 3).
- 커버 주문 메모는 v4와 같다: "Top face (flat side without bosses) is cosmetic. Please put supports on the boss side only." 두 단 커버의 턱 윗면과 바닥 윗면이 모두 보이는 면이다.
- STL은 FDM용 방향(뒤집은 부품은 X축 180°, `tools/orient_print_stl.py --flip`, 베드에 닿을 면이 Z = 0)이고 MJF·레진에서는 참고용이다. STEP은 조립 좌표 그대로다. 업체에는 STL을 올린다.
- 자석은 Ø3×2 **10개**(보스 6 + 다리 4). 다리 쌍은 자석끼리 붙으므로 극성이 있다(v5 문서 §2).

## 재현·검사

```powershell
python tools/export_print_v5.py                      # order2 STL/STEP + inspection/data/seam-v5-print-set.json + seam-v5-mjf-thin-wall.json
python -B inspection/scripts/verify_seam_v5.py       # 해시·성분·부피·벽·크기, spine/브래킷/게이트 = v4 확인(print_set)
```

`inspection/data/seam-v5-print-set.json`은 v4의 `seam-v4-print-set.json`과 같은 형식이다(`print_flip_about_X`, CAD/STL 부피, 출력 방향 크기, 해시). 얇은 벽 검사 결과는 `seam-v5-mjf-thin-wall.json`에 조립 좌표로 매핑되어 있다. STL 8개는 모두 연결 성분 1, 열린 모서리 0, CAD 대비 부피 오차 < 0.01 %다.
