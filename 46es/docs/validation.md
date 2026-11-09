# 검증과 다음 작업

현행 **v5, 주문 전(시험 출력 대기)**. CAD 검사 통과 ≠ 실물 통과.

## 변경 유형별 확인

| 변경 | 최소 확인 | 비고 |
|---|---|---|
| 문서/링크 | `python -B 46es/tools/check_repository.py`; stage 후 `update_manifest.py --check` | CAD/실물 불필요 |
| 정적 검사/manifest 로직 | 위 + 관련 동작 확인 | CAD 재생성 불필요 |
| v5 형상/생성기/샘플 원본 | 현행 CAD·제작 세트 갱신 및 형상 검사. 조립 모델에 영향이 있으면 검토 CAD 갱신 후 가이드 시각 검토 | SolidCraft/NumPy/SciPy. 실물 별도 |
| 가이드 spec/3D/자산 | [시각 검토](../guide/README.md#시각-검토)로 변경 단계 확인. 화면·조작이 바뀌면 데스크톱·모바일 브라우저 검사도 수행 | Playwright 필요 |
| 출력물/주문 세트 | STL 연결성·모서리·부피/경계/방향/해시, 제작 안내·manifest | 업체 출력 품질 별도 |
| 실물 시험 | 아래 목록 기록, 통과/수정/보류 | CAD와 별개 |

미실행은 `미실행`, 실물은 `실물 확인 대기`로 표기. 과거 `ok` JSON 재사용 금지.

## 실물 확인 목록

| 확인 항목 | 확인 방법·다음 결정 |
|---|---|
| 스위치 체결 | 주문 1 B 쿠폰 행 C에서 13.7–14.3 홀을 시험. 삽입력·걸쇠·키캡 제거 시 이탈·플랜지 착좌 기록 |
| 마운트와 스위치 핀·배선 | 실물 확인 대기. r2 배열 기준 왼쪽 10·11번, 오른쪽 18·33·46번에 실제 5핀 스위치를 조립한다. 센터·양쪽 다리·납땜 단자·다이오드·배선이 닿거나 눌리지 않는지 확인한다. 타건 및 반복 탈착 후 포켓 둘레의 휨·균열과 받침 들뜸을 확인한다. |
| mount·케이스 | 실물 확인 대기. 마운트 4개를 PSD60에 장착하고 GH60 위치, 장공, 나사와 지지대 포켓을 확인한다. 오른쪽 H06과 케이스 벽 사이 여유, Rear를 넣고 뺄 때의 공간, 심 받침과 배선의 접촉을 확인한다. plate를 얹고 받침 7곳의 접촉을 얇은 종이나 필러 게이지로 확인한다. |
| 앞 이음 | L/R 쿠폰을 맞추고 M2×5 체결. 단차·흔들림·삐걱임 확인 후 가공 또는 접착 결정 |
| 자석·보스 | Ø3×2 자석과 투명 보스 탭/검정 쿠폰 조합으로 끼움·흡착·에폭시·표면 확인 |
| 케이스 내측 폭 | 전체 폭 285.781의 실제 접촉과 중심 맞춤 확인. 현재 대략값이면 편측 약 0.11 여유 |
| 키캡 스커트 높이 | r2 upper plate 윗면 → 스커트 밑면을 쉴 때·끝까지 눌렀을 때 측정. 쉴 때 간격 g이면 `v5_keycap_bottom_above_seat = 2 + g` |
| 케이스 테두리 높이 | 지지대 상면 기준 앞·뒤 측정. 현재 14는 대략값 |
| 배선·Pro Micro·USB | 실제 부품·플러그·배선 돌출과 분해 여유 확인. 배선은 가이드 3D 형상이 없음 |
| 컨트롤러 스냅 | 실물 확인 대기. 주문 1 스냅 브래킷 A·B·C에 실제 Pro Micro를 끼운다. 맨보드 끼움·해제 → 패드 5–12번 16선 납땜 뒤 plate·mount를 단 상태에서 끼움·해제(암 해제 접근) → USB 쪽 당김에 모서리 턱 → 끝 립·암 립이 부품면 부품·납땜에 닿지 않는지 → 10회 탈착 뒤 암 균열·영구 처짐. 결과로 `ctrl5_hook_e`·`ctrl5_end_d`를 정해 `tools/ctrl_v5.py`에서 다시 만든다. CAD 변형률(삽입 1.75 %)은 실물 강도를 보증하지 않는다 |
| Pro Micro 실측(M15) | 실물 확인 대기. 보드 L·W·두께, 패드 위치(가정: 1번 핀 USB 끝에서 3.8, 열은 긴 변에서 1.27 = 검토 모델 참고 도면), 부품면 가장자리 부품(가정: +X 끝 크리스털 0.7), USB 실드 다리. 다르면 `ctrl_v5` 상수와 검토 모델 참고 형상을 함께 고친다 |
| 스위치 다리와 Pro Micro | 실물 확인 대기. 1번(+x)·23번(−x) 스위치 PCB 다리가 검토 CAD에서 Pro Micro 뒤 모서리에 0.86 mm 파고든다(`assembly-reference-v5-verification.json` controller). 실제 스위치로 확인하고 가이드 ctrl 단계대로 자른다 |
| 본 출력 후 커버 | 얇은 앞·뒤 베젤(약 1.16–2.76)의 강도·휨, 위 다리 들뜸, 키캡 풀러 접근, 투명도·기포 확인 |

주문 1 통과 후 주문 2를 넣는다. 시험으로 형상을 바꾸면 출력물·검증·가이드를 다시 만든다. 커버 창 여유 1.0은 현재 요구이므로 시험 실패를 이유로 자동 축소하지 않는다.

## 재생성 (저장소 루트)

SolidCraft CLI와 Python NumPy·SciPy가 설치된 Windows 환경에서 실행한다. 현재 CAD 도구는 기본 설치 경로 `C:/Program Files/SolidCraft/solidcraft-cli.exe`를 사용한다. 가이드만 `--cli`로 경로를 지정할 수 있다.

```sh
python 46es/tools/build_seam_v5.py --mounts   # mount만 바꿀 때: 수 초, 도면 단면 비교
python 46es/tools/build_seam_v5.py
python 46es/tools/export_seam_v5_review.py
python 46es/tools/export_print_v5.py
python 46es/tools/export_print_v5.py --trial
python -B 46es/inspection/scripts/verify_seam_v5.py
python 46es/tools/build_assembly_reference_v5.py
python -B 46es/inspection/scripts/verify_assembly_reference_v5.py
python 46es/guide/build_guide.py
```

`--trial`은 현행 모델의 mount·이음 쿠폰과 `model/samples/46es_sw_hole_sample.sc`의 B 쿠폰·보스 탭을 내보낸다. 샘플 행 C `SMP_upper`는 1.7이어야 한다. 두 주문의 내보내기는 `46es/.cache/print_v5/`에서 CAD 재평가, STL 검사와 벽 스캔을 마친 뒤 각 세트를 교체한다. 각 부품 기록에 실제 내보내기에 사용한 CAD와 STL/STEP 해시가 들어간다. 현행 CAD 해시가 바뀌면 그 모델을 사용한 두 세트를 갱신한다.

`verify_seam_v5.py`는 고정 기준 CAD의 해시·미변경 바디·CSV·커버 높이·벽·간격·주문 2 출력물을 검사한다. mount 4개는 주문 1 STL의 단면(Z 1.0·2.5·3.6·6.0)을 `model/mounts_cadcraft_phase1.dxf`와 매개변수로 만든 기준 프로파일과 비교하고, 팔각 랜드 보존·육각 포켓 벽·층별 부피를 확인한다. 받침은 plate 밑면과의 접촉 면적 및 간섭을 CAD에서 검사하고, 실제 하중·공차·배선은 시험 조립에서 확인한다. 검증 결과 JSON은 다시 실행할 때 생성되는 기록이며 수동으로 통과 상태를 고치지 않는다.

`verify_assembly_reference_v5.py`는 마운트 4개를 46키의 센터·양쪽 다리·금속 단자 참고 형상과 3D 비교한다. 설계 하한은 0.4 mm다. 참고 형상에 납땜과 배선은 포함되지 않으므로 실제 간섭과 강성은 위 실물 시험에서 확인한다. 변경이 조립에 영향을 주면 [가이드 시각 검토](../guide/README.md#시각-검토)에서 해당 단계와 완성 상태까지 확인한다.

## CAD 없이 할 수 있는 검사

```sh
python -B 46es/tools/check_repository.py
python -I 46es/tools/update_manifest.py --check
```

첫 명령은 현행 경로·문서 링크·가이드 부품 참조·CAD/CSV·입출력 해시·시험/본 출력 STL의 연결성·모서리·부피·기록을 검사한다. SolidCraft의 재평가·간섭 계산이나 브라우저 조작을 대신하지 않는다. 가이드 브라우저 검사는 [가이드 안내](../guide/README.md)를 따른다.

파일 추가·변경·삭제 뒤 `git add 46es` → `update_manifest.py` → `git add 46es/manifest.json`을 실행한다. CI는 현재 목록·문서·출력물 불일치를 차단한다.

텍스트는 `.gitattributes`로 LF를 고정한다. 정리 전 조립 메타데이터의 실측 JSON 해시는 Windows CRLF 사본의 값이었다. 원본 관찰값과 CAD는 바꾸지 않고 Git에 저장된 LF 바이트의 해시로 정규화했다.
