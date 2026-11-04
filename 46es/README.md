# 46es — 46키 non-split handwired keyboard

PSD60 Defender 하우징용 **46키 non-split hand-wired 키보드**의 기존 아크릴 구조와 `46es_r2_keyboard.dwg`(3D 프린팅 리비전)를 바탕으로 배선·체결·커버 구조를 개선하는 프로젝트입니다. **46sp는 별도의 split keyboard 참고 예시이며 46es 원본이 아닙니다.**

## 자료

- [전체 논의와 다음 버전 계획](docs/planning.md)
- [PSD60 체결·Pro Micro·점검성 설계 기준](docs/assembly-revision.md)
- [기존 3D 프린팅 리비전 DWG](cad/46es_r2_keyboard.dwg)
- [46키 펌웨어 설정 JSON](firmware/46es_kbfirmware.json)
- [파일 체크섬과 크기](manifest.json)

![DWG 내장 미리보기 — 치수 확인용 아님](images/46es_r2_keyboard_preview.png)

## 설계 방향

PSD60 → GH60 기준 하부 프레임 → 육각 스탠드오프 → 46es Plate(5T 구조부·국부 1.5T 스냅 체결 후보) → 별도 Cover. Pro Micro는 교체 가능한 브래킷과 분리형 커넥터를 우선 검토합니다. 치수는 실물 검증 전입니다.

Plate 코너는 모따기로 간섭을 피하고, cover는 R별 코너 샘플로 현물 적합성을 확인합니다. 스위치 홀은 아크릴의 14mm 체결 결과를 출발점으로 하되 출력 오차와 걸쇠용 하면 파임을 시험합니다.

## 확인 범위

펌웨어 JSON은 46키와 4×12 전기적 매트릭스를 확인했습니다. 실제 배선·동작 시험이나 빌드는 수행하지 않았습니다. DWG는 내장 미리보기만 확인했고 정밀 형상은 아직 읽지 못했습니다. GH60 체결 좌표와 Wedge의 R값은 PSD60 실물에서 검증하기 전의 참고값입니다.

기존 46sp 아크릴 도면·사진과 Wedge STL은 이번 업로드에 포함되지 않았습니다. 해당 자료는 업로드 시 기존 로컬 경로에서 읽히지 않았으며, 앞선 분석 기록과 참고 링크는 계획 문서에 유지했습니다. 외부 모델의 재배포 권한은 확인하지 않았습니다.
