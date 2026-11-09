# v5 조립 가이드

`guide_v5.json`(설명) + `assembly_v5.json`(3D 단계) + `model/46es_assembly_review_v5.sc` → 정적 웹 가이드. 게시: https://zzskm.github.io/keyboard-46es/ (`/v4/`는 과거 기록, 현행 생성 대상 아님).

설명/재료/구매 수량=spec, 부피/경계/렌더/본문 숫자=CAD, 실측 상태=`model/measurements.csv`. 검토 CAD 실측 원본=`model/measurements/2026-11-04T111846Z.json`(역할 다름, [측정 안내](../model/measurements/README.md)).

## 실행 (저장소 루트)

SolidCraft CLI + Python NumPy·Matplotlib·Shapely·ezdxf 필요(기본 `C:/Program Files/SolidCraft/solidcraft-cli.exe`, `--cli` 변경).

```sh
python 46es/tools/build_assembly_reference_v5.py
python -B 46es/inspection/scripts/verify_assembly_reference_v5.py
python 46es/guide/build_guide.py
python -m http.server 8766 --bind 127.0.0.1 --directory 46es/guide/out
```

`http://127.0.0.1:8766/#interactive`. 원본 CAD/측정 JSON/생성기/검토 CAD 해시 불일치 시 중단.

- `--skip-renders`: 유효 캐시 재사용(없으면 실패). `--only hero,st-ctrl`: 일부만.
- `--out PATH --clean-img`, `--jobs N`(기본 4).

`.cache/`, `out/`, `out_*/`는 생성물(Git 제외).

## 게시

```sh
python 46es/guide/publish_guide.py            # origin/main에 있는 깨끗한 커밋에서
python 46es/guide/publish_guide.py --dry-run  # 빌드·브라우저 검사만
```

한 번에 빌드(`out_publish/`) → 브라우저 검사 → Pages clone(`D:/work/zzskm.github.io`)의 `keyboard-46es/`에 복사(`v4/` 유지) → 커밋·push → 게시본 확인까지 한다. 46es에 미커밋 변경이 있거나, HEAD가 origin/main에 없거나(`--allow-branch`로 완화), Pages clone 작성자가 zzskm noreply가 아니면 멈춘다. 빌드마다 `build.json`(원본 커밋·검토 모델 해시·파일 해시)을 넣고, `https://zzskm.github.io/keyboard-46es/build.json`이 이 커밋을 가리키고 `index.html`이 같아질 때까지 기다린다(기본 15분). 이 저장소 커밋만으로는 게시가 갱신되지 않는다.

## 시각 검토

형상·체결·배치·조립 순서·부품 설명이 바뀌면 변경 단계와 완성 상태를 확인한다. 먼저 조립 검토 CAD를 갱신하고 위 검사를 실행한다. 다음 명령은 현행 CAD에서 로컬 조립 뷰를 빌드한 뒤 브라우저에서 지정한 단계와 마지막 단계를 열고, 2D 조립도와 3D 캡처를 남긴다. 시각 검토용 빌드는 게시 가이드의 정적 CAD 스냅샷 생성을 생략한다. Playwright와 Chrome이 필요하며 다른 Chromium 실행 파일은 `BROWSER_EXECUTABLE`로 지정한다.

```sh
# 예시: 마운트와 컨트롤러 변경 검토
python -B 46es/guide/review_guide.py --steps standoff trial ctrl wire module --views iso bottom
```

명령이 출력하는 `guide/.cache/visual-review/`의 실행 폴더에는 로컬 `site/`, 캡처와 `review.json`이 들어간다. 기록은 원본 CAD·검토 CAD 해시, 실제 단계 ID·제목, 이미지 파일을 묶는다. 캡처 후에는 부품 표시·강조·수량, 체결 방향, 설치 및 분해 접근 공간을 눈으로 확인하고 변경 보고에 판정을 적는다. 예를 들어 마운트 변경이면 장착 단계와 plate를 얹은 상태를 함께 확인한다. 자동 캡처 직후 기록 상태는 `pending_manual_review`다.

가이드 화면·3D 조작을 바꿨다면 아래의 전체 브라우저 검사로 데스크톱·모바일과 3D 실패 대체 화면도 확인한다. 기존 게시 자산으로 UI만 확인했다면 `UI 미리보기`, 실행할 수 없었다면 `미실행`, 가이드에 영향이 없는 정리라면 `대상 없음`으로 보고한다.

## 그림

`diagrams.py`가 조립 단계 그림(SVG)을 만든다. 손으로 그리지 않고 CAD 생성 원본에서 읽는다: 배선 지도·키캡 폭(키 위치 `tools/make_key_dxf.py`, mount 윤곽 `tools/mounts_v5.py`, plate·spine 범위는 검토 CAD), Pro Micro 핀 배치·스냅 끼우기/빼기(`tools/ctrl_v5.py`), 행·열·핀(`firmware/46es_kbfirmware.json`), 스위치 번호 ↔ 펌웨어 키(`matrix_v5.json`, 범례·키 폭으로 대응, 10·11번 Esc/Tab 순서는 미확인). 단계의 `diagrams`에 그림 ID를 적는다(`magnet-polarity`, `snap`, `wiring-map`, `pinmap`, `diode`, `test-grid`, `keycaps`). 빌드는 대응이 일대일인지, 행이 CAD X 순서인지, 검토 CAD의 Pro Micro 위치가 `ctrl_v5.py`와 같은지 확인한다.

## spec

`groups`=CAD 바디 패턴+`@그룹`. `renders`=표시/카메라/단면. 본문 토큰 `{{p:}} {{v:}} {{d:}} {{n:}}`. yaw 0=−Y(앞), −π/2=+X. 조립 단계 ID/구매품 ID는 체크·진행 기록에 쓰이므로 변경 금지. 3D 단계는 `assembly_v5.json`(`show,focus,needs,view,hardwareStages`). 배선은 3D 형상 없음, 케이스/하드웨어/키캡은 참고. `assets/vendor/`=Three.js 0.180.0+MIT(오프라인). 3D 뷰어는 버튼 클릭 시 로드.

## 비교/검토/검증

`comparison_r2.json`=DWG 판 윤곽·두께·배치 가정(공칭/가정). `model/reference_r2/` STEP/STL. 갱신: `python 46es/tools/build_r2_reference.py`(CadQuery 2.6, ezdxf).

3D 시점 버튼: `시점 복원`(`data-view=reset`)은 단계 기본 시점, `입체`·`위`·`아래`·`앞`은 고정 시점이다. `review_guide.py --views`도 같은 이름을 쓴다(`reset iso top bottom front`). 그림이 있는 단계는 `<단계>-diagrams.png`도 남긴다.

SolidCraft 없는 UI 검토: `python 46es/guide/preview_from_published.py --published <v5 자산 폴더>`(`assembly.json,models/,img/`, 해시 일치, Pillow). 정식 빌드 대체 아님.

검증: `python -B 46es/tools/check_repository.py`(경로/참조, CAD 재평가·브라우저 아님). 브라우저: `python 46es/guide/check_browser.py --site 46es/guide/out`(Playwright, 폴더를 직접 띄움. 실행 중인 서버는 `GUIDE_URL`, 그 밖에 `BROWSER_EXECUTABLE/GUIDE_SHOT_PREFIX`). 단계·부품 수는 빌드의 `assembly.json`에서 읽는다.
