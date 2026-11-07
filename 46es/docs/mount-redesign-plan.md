# v5 구조 개선 로드맵 (계획)

Phase 1의 CAD와 주문 1 디지털 검증을 완료했다. 제작 조건과 실물 시험은 [검증 목록](validation.md)과 [주문 안내](../model/print_v5/README.md)에서 관리한다.

## 로드맵
1. **Mount 개선** — keyswitch leg/pin 충돌 회피, 불필요 형상 제거, 단순·직선화.
2. **Ctrl bracket 개선** — Pro Micro 브래킷/게이트/체결/배선·USB 간섭을 단순·안정적으로 개선.
3. **Mount + Ctrl/Spine 병합** — 역할/경계 재정의 후 부품 수·체결·조립 복잡도 축소(가능 범위에서).

원칙: 단계별로 분리 검증. 3단계는 1·2단계의 형상/인터페이스가 안정된 뒤 진행.

## 1단계 — Mount 개선

- `build_seam_v5.py`에서 네 마운트의 WEB 5개를 억제했다. 기존 바디 ID, GH60/PSD60 체결 기준과 Z 8의 plate 받침 7곳을 유지한다.
- 좌우 마운트의 r2 배열 번호 10·11·18에 핀 회피 포켓을 두었다. H02의 spine shim 가장자리에는 아래쪽 보강을 추가하고 Z 3.95 받침 높이를 유지한다. H02의 해당 벽 두께는 0.95 mm에서 1.45 mm로 개선됐다.
- 스위치 착좌면 Z 11.3을 기준으로 센터·다리·금속 단자를 모델링했다. KS-3X1 도면의 XY 배치와 착좌면 아래 8.6 mm의 보수적인 참고 깊이를 사용한다. 46키와 마운트 4개를 3D 비교하며 최소 설계 여유 0.4 mm에 대해 CAD 최솟값은 0.60 mm였다. [Gateron KS-3X1 Yellow 도면](https://cdn.shopify.com/s/files/1/0565/8070/2297/files/SPEC-KS-3Y10B050NW-X1-Yellow_Switch.pdf?v=1675841028)
- 주문 1에는 현행 v5에서 재생성한 마운트·이음 쿠폰과 행 C 1.7 mm의 B 쿠폰·자석 포켓이 있는 보스 탭을 함께 사용한다. 원본 CAD와 STL/STEP 해시는 [시험 출력 기록](../inspection/data/seam-v5-trial-print-set.json)에 연결한다.
- 실물 확인 대기 항목은 마운트 강성, 실제 5핀·납땜·배선, PSD60 체결과 7곳의 받침 접촉이다.

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
