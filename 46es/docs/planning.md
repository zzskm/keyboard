> **역사 문서(현행 v5 기준 아님).** 이 문서는 작성 당시의 계획/실험/검토 기록이다. 현재 설계·제작·검증 판단은 [README](../README.md), [설계](design.md), [검증과 다음 작업](validation.md), [v5 제작 세트](../model/print_v5/README.md)를 우선한다. 필요한 결정/근거만 현행 문서로 옮긴다.

# 46키 non-split handwired keyboard — 다음 버전 사전 검토

작성일: 2026-11-03

> **프로젝트 구분:** 46es는 실제 제작 중인 46키 non-split 키보드다. **46sp는 별도의 split keyboard 예시 도면**이며 46es의 원본이나 키 개수 검증 대상이 아니다. PSD60 결합·MCU·정비 설계 기준은 [assembly-revision.md](assembly-revision.md)에 정리한다.

## 1. 목적과 현재 상태

현재 사용 중인 아크릴 버전의 키보드를 바탕으로, 배선과 결합 구조를 개선한 3D 프린팅 버전을 계획한다. 현재 단계는 전체 출력 발주 전 자료 수집 및 구조 검토 단계다.

- 대상은 **46키 non-split handwired keyboard**다.
- 좌우 키 영역은 나뉘지만 하나의 하우징에 들어간다. 물리적으로 분리된 split 키보드 제작이 아니다.
- PCB 없이 스위치 아래에서 직접 배선하는 구조다.
- 현재 버전은 아크릴 부품을 조립하여 사용 중이다.
- 기존 구조부의 Plate는 5T를 기준으로 논의했다. 새 3D 프린팅 버전의 스위치 걸쇠 체결부는 국부적으로 약 1.5T를 유지하는 방안을 우선 시험한다. 전체 Plate를 1.5T로 확정한 것은 아니다.
- 하우징은 **KPrepublic PSD60 Defender**다.
- 기존 케이스 나사 중 일부로 체결했지만, 막대 형태 부품으로 위치를 억지로 맞춘 상태라는 사용자 설명이 있었다. 따라서 현재 체결 구멍을 정확한 기준 좌표로 그대로 복제하지 않는다.
- 기존 결합에 육각 인서트/육각 스탠드오프를 사용하고 있다. 대화에서는 프레임–plate 연결에 육각 스탠드오프를 재사용하는 방향으로 정리했으며, 실제 부품 형식·규격은 추가 확인한다.

현재 버전 사진:

- `미디어 (1).jpg`

## 2. 용어 정리

이 논의에서 low/high profile은 스위치 종류나 스위치 자체 높이를 뜻하지 않는다.

- **Low profile 구성:** 측면에서 keycap과 plate 사이의 간격이 노출되는 형태.
- **High profile 구성:** plate에 추가 파츠를 붙여 측면 간격 또는 스위치 주변을 가리는 형태.
- **Plate:** 스위치를 지지하는 구조. 46es r2 DWG의 2D 형상은 [검사 보고서](../inspection/46es_r2_dwg_inspection.md)에서 해석해 DXF로 내보냈다. DWG에 Z·두께 정보가 없으므로 조립 형상(행별 높이·적층)은 현물 실측(M12·M21) 후 확정한다. 펼쳐진 46sp 부품의 형상은 별도 참고 사례다.
- **Cover:** 키 영역 주변과 중앙 등의 빈 공간을 덮는 파츠. 정확한 분할과 높이는 앞으로 설계한다.
- **하부 마운트 프레임:** 케이스의 체결 위치와 사용자 정의 plate의 체결 위치를 연결하는 부품.

초기 대화에서 스위치 높이와 하우징 높이를 혼동했으나, 이후 위 의미로 정정했다.

## 3. 현재 유력한 결합 구조

```text
PSD60 Defender 하우징
  └─ 하부 마운트 프레임: GH60 기준 위치로 케이스에 체결
       └─ 육각 스탠드오프
            └─ 46es Plate 및 지지 구조 (5T 구조부 + 국부 약 1.5T 스냅 체결 시험)
                 └─ 별도 체결 cover
```

### 역할 분담

| 부품 | 역할 |
|---|---|
| 하부 프레임 | 케이스 고정, plate 지지, 배선·컨트롤러 공간과의 간섭 회피 |
| 육각 스탠드오프 | 프레임–plate 연결, 높이 확보 |
| Plate | 스위치 위치·높이·각도 유지, 스위치 고정 |
| Cover | 측면 틈과 빈 공간 가리기, 외관 형성 |

### 설계 방향 — 아직 최종 확정 아님

- 별도 레이어를 계속 추가하기보다 하부 프레임이 plate 지지와 필요한 배선 고정 기능을 함께 맡게 한다.
- 하부 프레임은 꽉 찬 판보다 필요한 지지점을 연결하고 중앙을 비운 구조를 우선 검토한다.
- 케이스 체결 위치와 프레임–plate 체결 위치를 분리한다. 후자는 배선과 스위치를 피해서 자유롭게 설계할 수 있다.
- Plate와 handwiring을 한 덩어리로 들어낼 수 있는 정비 구조를 목표로 한다.
- Cover를 분리하기 위해 케이스 고정부터 전부 해체하지 않도록 조립 순서를 고려한다.
- Plate 고정 나사에 위에서 접근할 수 있도록 한다.
- 컨트롤러를 하부 프레임에 고정한다면 plate를 들어낼 때 연결선을 분리할 커넥터 또는 작업 여유 길이를 고려한다.
- 스탠드오프 높이와 배선 공간은 케이스 지지대 상면에서 plate 밑면까지의 실제 공간을 측정한 뒤 정한다.
- 스탠드오프 고정 나사 머리, 공구 접근 공간, 분해 중 스탠드오프의 동반 회전을 검토한다.

## 4. 도면 없는 하우징에 맞추는 방법

### 나사홀

초기에는 현물 전사와 후가공을 검토했으나, GH60 자료가 확보되어 **GH60 좌표로 설계한 뒤 현물에서 검증**하는 방향으로 바뀌었다.

- GH60 좌표를 이용해 얇은 체결 시험 프레임을 먼저 만든다.
- 모든 나사가 프레임을 억지로 휘거나 밀지 않고 들어가는지 확인한다.
- 필요한 경우 첫 시제품의 가공 여유 영역에 위치를 전사하고 드릴로 보정한다.
- 가공할 때는 출력 부품을 케이스에서 분리하여 기존 나사산 손상을 피한다.
- FDM 후가공 예정 영역은 빈 인필이 노출되지 않도록 충분한 솔리드 영역을 지정한다.
- 확정한 구멍 위치는 CAD에 반영하여 다음 출력부터 재현한다.
- 구멍을 무작정 크게 만들어 위치 오차를 가리는 방식은 피한다. 위치 확인과 조립 여유 설정을 구분한다.

전사용 나사(transfer screw)로 중심을 전사하는 방법도 대안으로 논의했다. 이 방법은 평면 중심을 얻는 용도이며 지지대 높이를 제공하지 않는다.

### Plate 코너

- 하우징 내측 R을 정밀 복제하는 대신 적절한 모따기로 코너 간섭을 피하는 방안을 검토했다.
- 체결부, 스위치 주변, 지지부의 필요한 살은 유지한다.
- GH60 나사 배치가 같다는 이유만으로 하우징 내측 R까지 동일하다고 가정하지 않는다.

### Cover 코너

- R이 다른 작은 코너 샘플을 출력해 실물에서 선택한다.
- 샘플은 단순 곡선 조각이 아니라 실제 벽 두께, 결합 턱, 삽입 깊이를 포함한다.
- 필요하면 인접 키 영역의 경계도 넣어 키캡 간섭을 함께 확인한다.
- 직선 구간의 조립 여유와 코너 R을 별도로 검토한다.
- 케이스 안으로 들어가는 둥근 직사각형 외곽에서는 가로·세로 치수가 같을 때 R을 크게 하면 코너 재료가 더 제거된다.
- 코너를 최종 교체 파츠로 남기는 방법도 가능하지만 이음새와 고정부가 추가된다. 우선은 샘플로 R을 정한 뒤 최종 cover를 제작하는 방안을 논의했다.

## 5. 스위치 홀과 5T plate

### 검증된 사항

- 사용자가 **현재 아크릴의 14mm 홀에서 타이트한 체결을 검증**했다.
- 이 결과는 해당 아크릴 가공품과 사용 스위치 조합의 결과다.
- 14mm 설계 치수를 3D 출력에 그대로 적용했을 때 동일한 끼움이 나온다고 확정할 수는 없다.

### 마찰 고정과 스냅 고정의 구분

- 5T를 그대로 관통한 홀에서는 스위치 걸쇠가 판 아래로 나오지 못할 수 있다.
- 타이트한 마찰 고정과 걸쇠가 펴져 고정되는 스냅 체결은 다르다.
- Handwired 구조는 PCB가 스위치를 지지하지 않으므로 고정 방식 검증이 중요하다.

### 검토한 단면

- Plate 전체 두께는 5T로 유지한다.
- 스위치 홀 주변을 하면에서 확대하거나, 걸쇠가 있는 두 영역만 국부적으로 파낸다.
- 스위치 상단 턱은 plate 상면에 앉고 걸쇠는 얇게 남긴 부분 아래에 걸리도록 한다.
- 남기는 두께와 하면 파임 범위는 실제 스위치 장착 도면과 실물로 정한다.
- 일반 MX의 약 1.5T 장착부는 참고값으로만 논의했다. 사용할 스위치 모델은 아직 확인되지 않았다.

### 시험 출력

- 14mm를 출발점으로 하고, 실제 출력 조건에서 끼움을 확인한다.
- 필요하면 13.9 / 14.0 / 14.1 / 14.2mm 등의 홀 샘플을 비교한다. 이는 시험 후보이며 최종 권장 치수가 아니다.
- 샘플에는 걸쇠용 하면 파임도 포함한다.
- 삽입력, 걸쇠 작동, 흔들림, 키캡 제거 시 스위치 동반 이탈, 탈착 가능 여부를 확인한다.
- 최종 출력과 동일한 업체·재료·방향·후처리 조건을 사용하도록 협의한다.

## 6. 로컬 파일 확인 결과

### 46sp_plate_r3.dwg

> **별도의 split keyboard 참고용 도면.** 아래의 홀 개수와 전개 형상은 46es 키 수 또는 설계 누락 판단에 사용하지 않는다.

- 경로: `46sp_plate_r3.dwg`
- 파일 확인 및 내장 미리보기 추출 완료.
- DWG 기하 데이터를 직접 해석할 CAD 도구가 없어 실제 형상 검토는 DXF로 진행했다.
- 원본 DWG는 변경하지 않았다.

### 46sp_plate_r3.dxf

- 경로: `46sp_plate_r3.dxf`
- 단위: mm (`$INSUNITS=4`).
- ENTITIES: LWPOLYLINE 73개, MTEXT 2개.
- 엔티티 레이어는 모두 `0`이다.
- 행별 판, 탭/홈 결합으로 보이는 외곽과 지지 부품이 가공용으로 펼쳐져 있다.
- 이 **46sp 참고 도면**에서 약 14 × 14mm 사각 개구부 45개가 집계됐다. 이는 46es 목표 46키의 누락 증거가 아니다.
- 이 파일에서 GH60 전체 외곽이나 케이스 체결용 원형 나사홀은 확인하지 못했다.
- 폴리라인에 원호 bulge 값이 없어 이 도면에서 하우징 코너 R을 얻을 수 없다.
- 행별 높이·각도와 조립 후 상대 위치는 펼친 배치 좌표만으로 확정할 수 없다. 사진 및 현물과 대조한다.

생성한 확인 파일:

- `46sp_plate_r3_preview.png`: DWG 내장 미리보기.
- `46sp_plate_r3_entities.json`: DXF ENTITIES 추출 데이터.
- `46sp_plate_r3_inspection.png`: DXF 형상 확인 이미지.

### The_Wedge.stl

- 경로: `The_Wedge.stl`
- 바이너리 STL, 삼각형 104,486개.
- 모델의 주된 면 기울기를 약 5°로 보고 보정한 뒤 여러 높이의 단면에서 코너 원을 근사했다.
- 모델 숫자를 mm로 해석했을 때 원래 XYZ 바운딩 크기는 약 295.90 × 111.12 × 28.33이다. STL 자체에는 단위 정보가 없으므로 단위 가정이 포함된다.
- 내측 코너는 대체로 **R2.5**, 바깥쪽의 둥근 윤곽은 대체로 **R5.5**에 가까웠다.
- 이는 메시에서 추정한 값이며 원본 CAD 명목 치수 또는 PSD60 실측값이 아니다.
- 외측 R5.5는 측정한 둥근 윤곽을 뜻하며 모델의 모든 외곽 형상을 하나의 R5.5 둥근 직사각형으로 해석하지 않는다.
- Cover 시험 후보로 R2 / R2.5 / R3 / R3.5를 논의했다. PSD60에서 적합성은 미검증이다.

생성한 확인 파일:

- `The_Wedge_inspect.npz`: 메시 데이터.
- `The_Wedge_sections.npz`: 단면 데이터.
- `The_Wedge_sections.png`: 단면 확인 이미지.
- `Wedge_corner_z5.csv`, `Wedge_corner_z10.csv`, `Wedge_corner_z15.csv`: 일부 코너 단면 좌표.

## 7. 외부 참고 자료

### PSD60 Defender 제품 안내

https://kprepublic.com/collections/case/products/kp-poseidon-60-psd60-defender-de-60-cnc-coating-case-layer-painting-for-standard-60-mechanical-keyboard-pcb-xd64-bm60-ec-gh60

- 공식 안내에서 외형 약 320 × 115mm, 앞 높이 21mm·뒤 높이 32mm, 경사 6°를 확인했다.
- 내부 개구부, 코너 R, 지지대 높이와 상세 나사 위치 도면은 확인하지 못했다.
- PSD60, PSD60 Defender, PSD60 Gasket은 구분한다. 다른 모델의 외형 치수를 섞지 않는다.

### GH60 호환 치수 조사 문서

https://note.com/skeletonkbd/n/n7fdfaac9bd8c?hl=en

공개 CAD 비교 자료이며 실물 측정·장착 시험은 수행하지 않았다고 명시돼 있다. 원본 모델의 표시 자릿수는 제조 정밀도나 공차를 뜻하지 않는다.

GH60 PCB 앞쪽 왼쪽 기준점을 원점으로 하고, 키면에서 보았을 때 X는 오른쪽, Y는 뒤쪽이다. 단위는 mm다. **하우징 외곽의 앞쪽 왼쪽 모서리가 원점이라는 의미는 아니다.**

| 위치 | X | Y |
|---|---:|---:|
| H01 왼쪽 뒤 | 25.1993 | 66.6992 |
| H02 중앙 | 128.2 | 47.6 |
| H03 오른쪽 앞 | 190.4994 | 9.3993 |
| H04 오른쪽 뒤 | 260.0499 | 66.6992 |
| H05 왼쪽 가장자리 | 3.70934 | 38.0988 |
| H06 오른쪽 가장자리 | 281.29076 | 38.0988 |

- H01은 약 Ø2.5 원형, H02~H04는 약 5 × 2.5 가로 장공이다.
- H05·H06은 가장자리 컷아웃이며 좌표는 끝단 원호의 중심이다.
- 조사한 GH60 PCB 외곽은 285 × 94.6mm다.
- 문서의 286.2 × 96.3mm는 저자가 제안한 케이스 내측 치수 예시로, PSD60의 실제 내측 치수가 아니다.
- 문서의 R2는 USB 개구부 예시이며 하우징 코너 R이 아니다.
- PCB별 미세한 홀 차이가 있어 GH60 호환을 엄격한 공통 규격처럼 취급하지 않는다.
- 문서의 탈착식 지지대 권고는 여러 PCB를 받는 새 케이스 설계 맥락이다. 기존 PSD60의 지지대를 제거하기로 결정한 것은 아니다.

### help-14 GH60 plate 자료

https://github.com/help-14/keyboard-plate/tree/master/GH60

- `standard-plate.dwg`, `universal-plate.dwg`, `arrow-plate.dwg` 목록을 확인했다.
- GH60 및 표준 60% PCB용 설명이 있다.
- 개별 DWG 내부 형상·나사홀·R 수치는 아직 읽지 않았다.
- 향후 참고한다면 외곽과 체결 형상을 추출하고, 사용자 고유의 46키 배열과 구분한다.

### RAKKA 공개 설계

https://github.com/RAKKA-Keyboards/rakka-design/blob/master/rakka-60-atlas/README.md

- README에서 GH60 대응 홀을 포함한 DXF 및 STEP 자료를 안내한다.
- Plate–PCB 고정용 별도 구멍도 포함된다고 설명하므로, GH60 케이스 체결 홀과 구분해야 한다.
- 이번 대화에서 실제 CAD 형상을 추출·검증한 것은 아니다.

### GH-CAD-Resources

https://github.com/mohitg11/GH-CAD-Resources

파일 목록에서 다음 자료를 확인했다.

- `MXSpec.pdf`, `MX Series.pdf`
- `MXSwitchCuouts.png`
- `plate_components.dxf`, `plate_components.dwg`
- `MountStyles.pdf`

스위치 장착부와 plate 구성 자료의 후보이며 PSD60 전용 하우징 도면은 확인하지 못했다. 개별 파일의 내부 치수는 아직 검토하지 않았다. 별도로 CHERRY MX 문서도 참고했다.

https://cdn.sparkfun.com/datasheets/Components/Switches/MX%20Series.pdf

### Handwired 구조 예시

https://www.matsan.it/assets/images/posts/40/building-together.jpg

원문:
https://www.matsan.it/posts/QuattroZero/

- 이미지 파일 직접 열기는 실패했지만 원문의 제작 설명을 확인했다.
- Handwired, 적층 아크릴, 40% ortholinear 예시다.
- 배선·plate·하부 공간의 관계를 참고하는 자료이며 사용자 키보드와 배열·입체 형상이 같다고 가정하지 않는다.
- 이전 Google 썸네일 링크는 열리지 않아 이미지 내용을 확인하지 못했다.

### iGK60 plate 치수 이미지

https://www.pc-100.com/wp-content/uploads/gh60-mechanical-keyboards/iGK60-mechanical-keyboard-plate-mounting-dimension-size.jpg

설명 페이지:
https://www.pc-100.com/mechanical-keyboard-features-parameters/igk60-mechanical-keyboard-plate-mounting-dimension-size/

- 이미지 자체의 치수는 읽지 못했다.
- 제조사 설명은 plate–PCB에 뒤쪽 지지점 6개/M2, plate–케이스에 앞쪽 구멍 8개/M2.5를 명시한다.
- GH60의 6개 트레이 마운트 위치와 동일한 체결 구성으로 취급하지 않는다.
- PSD60의 홀 위치나 나사 규격을 이 자료로 확정하지 않는다.

## 8. 출력 대행 관련 논의

초기에는 국내 출력 서비스 후보로 다음을 살펴봤다.

- 크렐로: https://creallo.com/ko/services/3d-printing
- 아이컨택: https://eyecontact.kr/
- 3DFARM: https://3dfarm.co.kr/lp/print/

이는 직접 이용 경험에 따른 순위가 아니라 당시 공개된 주문·견적·가공 서비스 범위에 따른 후보 목록이다. 최종 업체는 선정하지 않았다.

현재 필요한 범위는 단순 출력뿐 아니라 설계, 현물 적합성 확인, 소형 샘플 출력이다. 실물 실측까지 맡길 경우 업체가 해당 작업을 제공하는지 별도로 확인한다.

- 출력 공정과 재료는 아직 결정하지 않았다.
- 넓고 얇은 부품은 SLS·MJF에서도 휨이 발생할 수 있으므로 출력 방식만으로 평탄도를 보장하지 않는다.
- 업체에는 전체 외형, 중요 체결 치수, 출력 방향, 후처리, 평탄도 요구를 함께 전달한다.
- 형상이 단순한 평판일 때 판재 가공을 비교할 수 있지만, 이번에는 입체 지지부·걸쇠 파임·배선 고정 등 3D 출력의 활용 가능성이 있다.

## 9. 아직 확정하지 않은 항목

| 항목 | 필요한 확인 |
|---|---|
| PSD60 실제 체결 배치 | GH60 시험 프레임과 실물 대조 |
| 케이스 지지대 | 높이, 상면 면적, 나사 규격·유효 깊이 |
| Plate 조립 형상 | 각 행의 위치·높이·각도, 좌우 상대 위치 |
| 스위치 | 정확한 모델, 걸쇠 위치와 장착부 두께 |
| 기존 육각 부품 | 스탠드오프/인서트 형식, 나사 규격, 길이 |
| 배선 | 다이오드·핀·교차 배선의 점유 높이, 경로와 고정점 |
| 컨트롤러·USB | 부품 크기, 위치, 고정, 케이블 경로와 분리 방법 |
| Cover | low/high 외관, 분할, 체결 위치, 키캡 작동 간섭 |
| 코너 R | Wedge 참고값과 실제 PSD60의 차이 |
| 출력 | 공정·재료·방향·후처리·끼움 보정량 |

## 10. 다음 작업 순서

1. **현 버전 조립 형상 복원**
   - **46es 기존 DWG**에서 추출한 2D 스위치 중심·회전각·외곽([검사 보고서](../inspection/46es_r2_dwg_inspection.md))을 현물과 대조하고(M12·M20), 행별 높이와 Plate 상면 위치를 실측한다(M21). 46sp DXF와 혼용하지 않는다.
   - 유지할 타이핑 형상과 개선할 구조를 분리한다.
2. **기준 좌표 설정**
   - GH60 체결 좌표를 하부 프레임의 기준으로 채택한다.
   - 46키 배열의 배치 기준과 연결해 조립 모델의 원점을 통일한다.
3. **하부 공간과 결합 설계**
   - 프레임, 스탠드오프, 배선, 컨트롤러, 공구 접근 공간을 배치한다.
   - Cover까지 포함한 조립·분해 순서를 확인한다.
4. **작은 검증 출력**
   - GH60 체결 시험 프레임.
   - 14mm 홀 및 걸쇠용 하면 파임 샘플.
   - R별 cover 코너와 결합부 샘플.
5. **현물 확인 후 CAD 보정**
   - 억지 조립, 키캡 간섭, 배선 압박, 스위치 이탈을 확인한다.
   - 변경 사항과 실제 검증 결과를 기록한다.
6. **전체 출력 견적·제작**
   - 검증한 설계와 출력 조건을 기준으로 견적을 비교한다.

## 11. 현재 결론

설계 및 시험 출력을 시작할 참고 자료는 충분히 확보됐다. 다만 **자료 수집 완료와 조립 설계 검증 완료는 구분**한다.

현 단계의 핵심은 추가 자료 탐색보다 **기존 입체 형상 복원, GH60 체결 확인, 스위치 스냅 단면과 cover 코너의 샘플 검증**이다. GH60 좌표는 기준 후보, Wedge의 R2.5는 시험 출발값이며 둘 다 PSD60 실물에서 검증한 값은 아니다.



## 12. Existing acrylic revision: 46es r2

The user supplied 46es_r2_keyboard.dwg as an existing design file, not a newly completed CAD design from this discussion.

> Correction 2026-11-04: this section first described the DWG as an existing 3D-printing revision. The user confirmed it is the design file of the **acrylic version**, which matches its MText sheet-material labels (acrylic, extruded plate, astel).

- DWG signature: AC1024. Embedded preview extracted; detailed geometry and dimensions have not been decoded. DXF/STEP export is needed for precise comparison.
  - Update 2026-11-04: the 2D geometry has since been decoded and exported to DXF; see [the r2 DWG inspection report](../inspection/46es_r2_dwg_inspection.md). The drawing has no dimensions and no Z/thickness data, so a STEP export would not add assembly heights (measure them as M21).
- Firmware JSON: 46 keys, 4 rows x 12 columns, 46 unique electrical matrix positions.
- Populated positions per row: 12 / 12 / 11 / 11.
- Unused matrix positions (zero-based): (2, 11), (3, 8).
- Row pins: D1, D0, D4, C6.
- Column pins: D7, E6, B4, B5, F4, F5, F6, F7, B1, B3, B2, B6.
- Displayed key widths: 43 x 1u, 1 x 1.25u, 1 x 1.75u, 1 x 2u.
- Layers 0-3 contain mappings; slots 4-15 are entirely KC_TRNS.
- controller=1, diodeDirection=0, bootloaderSize=2 are tool-specific enum values. Their physical meaning has not been verified against the original generator.
- All display rotations are zero. JSON display coordinates are not a mechanical drawing and do not encode the assembled plate curvature, height, or angles.
- The earlier 46sp DXF is a separate split-keyboard example. Its 45 square openings are not a 46es defect or missing-key indicator.

### Uploaded scope

This directory includes the accessible 46es DWG, original firmware JSON, embedded DWG preview, and planning notes. The separate 46sp split-keyboard example files, the assembled photograph, and The_Wedge.stl could not be read at their previous paths during upload preparation and are not bundled. Earlier analyses remain historical records. External reference-model redistribution rights have not been verified; links and measurement notes are retained instead.

## 13. 46es 리비전 결합·정비 요구사항 (2026-11-03)

설계 기준 상세: [PSD60 체결·Pro Micro·점검성](assembly-revision.md). 본 절은 기존 조사 기록을 최신 결정과 연결한다.

- **Mount**: PSD60 Defender의 GH60 포스트 → 개방형 Mount Frame → 스탠드오프 → 46es Switch Plate 순서. Top/Gasket Mount로 오인하지 않는다.
- **체결**: 하우징↔Frame 체결과 Frame↔Plate 체결을 구분한다. Cover를 떼고 위에서 Plate 나사에 접근하는 구조를 목표로 한다.
- **스위치**: 14×14 mm 홀과 약 1.5T 걸쇠 체결부는 출력 시험 후보. 5T 구조부는 유지하거나 보강 리브로 최적화한다. 키캡 스트로크 동안 Cover 간섭을 검증한다.
- **MCU**: Pro Micro는 개별 교체 가능한 브래킷에 장착하고, Plate의 4×12 매트릭스(16선)와 착탈식 커넥터로 연결한다. USB는 하우징 개구에 고정되는 연장 구조를 우선 검토한다.
- **정비**: USB 분리 → Cover 제거 → Plate 나사 제거 → 배선 커넥터 분리 → Plate 모듈 탈거. Frame 고정 나사는 Frame 교체 시에만 해체하는 것이 목표다.
- **미검증**: PSD60 실제 내부 치수·포스트 XY/Z·나사 규격·USB 개구·코너 R, 46es CAD 조립 치수 및 출력 공차. CAD 확정 전 현물/시험 지그 확인이 필요하다.

**이 문서는 설계 요구사항을 정리한 것이며 DWG 형상 변경이나 현물 검증 완료를 의미하지 않는다.**
