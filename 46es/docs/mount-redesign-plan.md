# v5 구조 개선 로드맵 (계획)

제작 조건과 실물 시험은 [검증 목록](validation.md)과 [주문 안내](../model/print_v5/README.md)에서 관리한다.

## 로드맵
1. **Mount 개선** — keyswitch leg/pin 충돌 회피, 불필요 형상 제거, 단순·직선화.
2. **Ctrl bracket 개선** — Pro Micro 브래킷/게이트/체결/배선·USB 간섭을 단순·안정적으로 개선.
3. **Mount + Ctrl/Spine 병합** — 역할/경계 재정의 후 부품 수·체결·조립 복잡도 축소(가능 범위에서).

원칙: 단계별로 분리 검증. 3단계는 1·2단계의 형상/인터페이스가 안정된 뒤 진행.

## 1단계 — Mount 개선

- SO1–SO6 랜드 외곽은 AF 8.5 mm로 통일한다. 육각 지지대 포켓, 원형 관통홀과 나사 머리 받침면을 보존한다.
- Rear의 옛 받침은 새 좌석 밖으로 돌출된 부분을 프레임 상면 위에서 정리한다. 새 plate 좌석과 spine shim 기준면을 유지한다.
- Front V 홈은 스위치 회피에 사용한다. SO6 보강은 컨트롤러 브래킷과 이음 너트에 여유를 둔다.

### 외곽과 체결부

- 기존 WEB 5개 억제에 이어 좌우 마운트의 외곽을 M3 체결점 두 곳을 잇는 직선 레일과 M2 체결점을 향한 가지 하나로 정리했다. 오른쪽 레일은 SO4·SO5를 따라 기울였고, H06 바깥쪽은 PSD60 참고 벽과 여유를 두도록 다듬었다.
- Rear의 안쪽으로 들어가던 외곽은 기존 프레임과 축소 마스크가 겹치는 경계에서 생긴 구간이다. H02와 SO3 사이를 직선으로 연결하고 spine shim 받침과 그 하부 보강을 유지했다.
- 왼쪽 10·11번과 오른쪽 18·33·46번의 r2 배열 위치에 핀 여유를 두었다. 회피부의 바닥은 조립 기준면에서 2.1 mm 위에 있다. 그림의 원형·장공 주변 돌출은 M2/M3 체결부이며, 짙은 받침은 Z 8 mm의 plate 접촉부다.

![세 마운트의 변경 전후 평면도. 모든 패널의 방향과 축척이 같다.](mount-phase1-outline.png)

### 디지털 검증과 실물 시험

- 스위치 착좌면 Z 11.3을 기준으로 46키의 센터·다리·금속 단자를 모델링했다. KS-3X1 도면의 XY 배치와 착좌면 아래 8.6 mm의 참고 깊이를 사용했다. 마운트 4개를 비교한 결과 핀 겹침은 0건이었다. 1.0 mm 탐색 범위에서 확인된 최단 여유는 L 0.567 mm, R 0.527 mm다. Rear와 Front에는 탐색 범위 안의 가까운 쌍이 없어 설계 하한 0.4 mm를 만족한다. [Gateron KS-3X1 Yellow 도면](https://cdn.shopify.com/s/files/1/0565/8070/2297/files/SPEC-KS-3Y10B050NW-X1-Yellow_Switch.pdf?v=1675841028), [조립 검증 기록](../inspection/data/assembly-reference-v5-verification.json)
- SolidCraft 솔리드 비교에서 대상 세 바디만 변경됐다. 조립 좌표계의 STL 단면을 겹쳐 변경 대상 3개 마운트의 체결부 10곳에서 홀과 나사 머리 지지면을 확인했다. Z 0 체결 기준면, Z 8 plate 받침, Z 3.95 Rear 심 받침도 확인했다. 비교 면적 차이는 최대 0.004 mm² 미만이었다.
- 조립 위치에서 검사한 마운트와 나사·스탠드오프, plate·spine, Pro Micro 및 스위치 하부의 비의도 체적 겹침과 미검사 쌍은 0건이다. 설계한 H06 바깥선은 측정 PSD60 벽 X=285.307 mm에서 0.257 mm 안쪽이다. 별도 Wilmore 케이스 참고 형상은 PSD60와 다른 치수이며, 그 비교에서는 오른쪽 외곽과 0.081 mm 겹친다. 케이스 치수 기록상 중심 정렬 시 편측 폭 여유는 0.109 mm다. Rear 연결부의 Z 0–17 mm 수직 이동 범위는 참고 케이스와 겹치지 않으며, SO3 하부 M3와의 최소 간격은 0.630 mm다. 실제 케이스의 공차와 탈착은 실물 확인 대기다.
- 현행 CAD 해시 `62cdb7de`에서 `standoff`, `trial`, `module`, `keycap` 단계의 조립도와 iso/top 캡처를 다시 만들고 수동 확인했다. 마운트 위치·체결 방향, plate 받침, 스위치·키캡 배치가 임시 조립부터 완성까지 이어지고, 화면에 빠진 마운트나 잘못된 체결 방향이 없었다.
- 주문 1의 마운트 4개는 각각 단일 연결 메시이며 비정상 모서리가 0개다. STL 벽 검사 최소값은 L 1.500 mm, R 1.121 mm, Rear/H02 1.203 mm, Front/H03 1.047 mm다. 모두 MJF 설계 하한 1.0 mm 이상이다. [시험 출력 기록](../inspection/data/seam-v5-trial-print-set.json), [시험 출력 벽 검사](../inspection/data/seam-v5-trial-thin-wall.json)
- 실제 5핀·납땜·배선, Rear 탈착 공간, PSD60 체결, 받침 접촉과 마운트 강성은 [실물 확인 목록](validation.md#실물-확인-목록)에서 관리한다.

## 2단계 — Ctrl bracket 개선

- `build_seam_v5.py`에서 `CTRL_LIP_*_SPLIT_V1` 4개, `CTRL_STOP_SPLIT_V1`, `CTRL_GATE_STOP_FINGER`를 억제했다. 브래킷·게이트가 단순·직선 형상으로 단순화됨.
- Pro Micro 삽입/탈거 경로에서 얇은 립과 스톱을 제거해 끼움·탈착 여유를 확보했다. USB 플러그·케이블 여유, M2 체결/너트 접근, 출력 방향·강성은 기존 유지(`CTRL_ROOF_WIRING_WINDOW`, `CTRL_GATE_M2_CLEAR`, 너트 포켓 보존).
- 1단계 마운트 형상과의 간섭은 `verify_seam_v5.py`에서 `overlaps: 0`, `contacts: 113`로 확인.
- `verify_seam_v5.py`에서 `SAME_AS_V4`에서 제외(볼륨 변경). 가이드·BOM·검증 갱신 필요.

## 3단계 — Mount + Ctrl/Spine 병합 (개요)
- 대상 후보: `MOUNT_*`, `PLATE_SPINE_V1`, ctrl bracket/gate 간 역할 통합.
- 목표: 부품 수/나사/조립 단계 축소, 배선·분해성 유지, plate 이음 지지 기능 보존.
- 제약: plate L/R 분할 구조·dovetail·spine 배선 홈/지지 역할 재검토 필요. 병합 시 body 이름/가이드 단계/출력 파일/검증 스냅샷 영향 큼 → 별도 설계 결정 후 진행.
- 선행: 1·2단계 완료, 간섭·강성·조립성 확인.

## 공통 검증
- CAD: `build_seam_v5.py` → review/export(`--trial`) → `verify_seam_v5.py`; 필요 시 assembly ref/verify → guide. mount/스위치 하부, plate/SO/M3/USB/ctrl 간섭 3D 확인.
- 정적: `python -B 46es/tools/check_repository.py`; stage 후 `update_manifest.py`/`--check`.
- 실물/미실행: `docs/validation.md`에 `미실행`/`실물 확인 대기` 기록. 주문 1 시험물 변경 시 혼용 금지, 해시/manifest 갱신.
