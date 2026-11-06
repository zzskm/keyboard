# 검증과 다음 작업

현행 설계는 v5이며 아직 주문 전이다. 저장된 CAD 검사 통과와 실물 제작 통과를 구분한다.

## 실물 확인 목록

| 확인 항목 | 확인 방법·다음 결정 |
|---|---|
| 스위치 체결 | 주문 1 B 쿠폰 행 C에서 13.7–14.3 홀을 시험. 삽입력·걸쇠·키캡 제거 시 이탈·플랜지 착좌 기록 |
| mount·케이스 | mount 4개를 PSD60에 장착. GH60 위치, 장공, 나사와 지지대 포켓을 확인한다. plate를 얹고 받침 7곳을 얇은 종이나 필러 게이지로 확인한다. 받침이 높으면 그 면만 다듬고, 낮으면 얇은 심으로 맞춰 흔들림과 plate 휨을 확인한다. |
| 앞 이음 | L/R 쿠폰을 맞추고 M2×5 체결. 단차·흔들림·삐걱임 확인 후 가공 또는 접착 결정 |
| 자석·보스 | Ø3×2 자석과 투명 보스 탭/검정 쿠폰 조합으로 끼움·흡착·에폭시·표면 확인 |
| 케이스 내측 폭 | 전체 폭 285.781의 실제 접촉과 중심 맞춤 확인. 현재 대략값이면 편측 약 0.11 여유 |
| 키캡 스커트 높이 | r2 upper plate 윗면 → 스커트 밑면을 쉴 때·끝까지 눌렀을 때 측정. 쉴 때 간격 g이면 `v5_keycap_bottom_above_seat = 2 + g` |
| 케이스 테두리 높이 | 지지대 상면 기준 앞·뒤 측정. 현재 14는 대략값 |
| 배선·Pro Micro·USB | 실제 부품·플러그·배선 돌출과 분해 여유 확인. 배선은 가이드 3D 형상에 없음 |
| 본 출력 후 커버 | 얇은 앞·뒤 베젤(약 1.16–2.76)의 강도·휨, 위 다리 들뜸, 키캡 풀러 접근, 투명도·기포 확인 |

주문 1 통과 후 주문 2를 넣는다. 시험으로 형상을 바꾸면 출력물·검증·가이드를 다시 만든다. 커버 창 여유 1.0은 현재 요구이므로 시험 실패를 이유로 자동 축소하지 않는다.

## 재생성 (저장소 루트)

SolidCraft CLI와 Python NumPy·SciPy가 설치된 Windows 환경에서 실행한다. 현재 CAD 도구는 기본 설치 경로 `C:/Program Files/SolidCraft/solidcraft-cli.exe`를 사용한다. 가이드만 `--cli`로 경로를 지정할 수 있다.

```sh
python 46es/tools/build_seam_v5.py
python 46es/tools/export_seam_v5_review.py
python 46es/tools/export_print_v5.py
python 46es/tools/export_print_v5.py --trial
python -B 46es/inspection/scripts/verify_seam_v5.py
python 46es/tools/build_assembly_reference_v5.py
python -B 46es/inspection/scripts/verify_assembly_reference_v5.py
python 46es/guide/build_guide.py
```

`--trial`은 현행 모델의 mount·이음 쿠폰과 `model/samples/46es_sw_hole_sample.sc`의 B 쿠폰·보스 탭을 내보낸다. 샘플 행 C `SMP_upper`는 1.7이어야 한다. 과거의 일회성 2→1.7 변환 스크립트는 현재 모델에 다시 실행할 수 없어 제거했다.

`verify_seam_v5.py`는 고정 기준 CAD의 해시·미변경 바디·CSV·커버 높이·벽·간격·주문 2 출력물을 검사한다. 받침은 plate 밑면과의 접촉 면적 및 간섭을 CAD에서 검사하고, 실제 하중·공차·배선은 시험 조립에서 확인한다. 검증 결과 JSON은 다시 실행할 때 생성되는 기록이며 수동으로 통과 상태를 고치지 않는다.

## CAD 없이 할 수 있는 검사

```sh
python -B 46es/tools/check_repository.py
python -I 46es/tools/update_manifest.py --check
```

첫 명령은 현행 경로·문서 링크·가이드 부품 참조·CAD/CSV·입출력 해시·시험/본 출력 STL의 연결성·모서리·부피·기록을 검사한다. SolidCraft의 재평가·간섭 계산이나 브라우저 조작을 대신하지 않는다. 가이드 브라우저 검사는 [가이드 안내](../guide/README.md)를 따른다.

파일 추가·변경·삭제 뒤 `git add 46es` → `update_manifest.py` → `git add 46es/manifest.json`을 실행한다. CI는 현재 목록·문서·출력물 불일치를 차단한다.

텍스트는 `.gitattributes`로 LF를 고정한다. 정리 전 조립 메타데이터의 실측 JSON 해시는 Windows CRLF 사본의 값이었다. 원본 관찰값과 CAD는 바꾸지 않고 Git에 저장된 LF 바이트의 해시로 정규화했다.
