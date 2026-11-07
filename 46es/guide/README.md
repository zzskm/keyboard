# v5 조립 가이드

`guide_v5.json`(설명) + `assembly_v5.json`(3D 단계) + `model/46es_assembly_review_v5.sc` → 정적 웹 가이드. 게시: https://zzskm.github.io/keyboard-46es/ (`/v4/`는 과거 기록, 현행 생성 대상 아님).

설명/재료/구매 수량=spec, 부피/경계/렌더/본문 숫자=CAD, 실측 상태=`model/measurements.csv`. 검토 CAD 실측 원본=`model/measurements/2026-11-04T111846Z.json`(역할 다름, [측정 안내](../model/measurements/README.md)).

## 실행 (저장소 루트)

SolidCraft CLI + Python NumPy·Matplotlib 필요(기본 `C:/Program Files/SolidCraft/solidcraft-cli.exe`, `--cli` 변경).

```sh
python 46es/tools/build_assembly_reference_v5.py
python -B 46es/inspection/scripts/verify_assembly_reference_v5.py
python 46es/guide/build_guide.py
python -m http.server 8766 --bind 127.0.0.1 --directory 46es/guide/out
```

`http://127.0.0.1:8766/#interactive`. 원본 CAD/측정 JSON/생성기/검토 CAD 해시 불일치 시 중단.

- `--skip-renders`: 유효 캐시 재사용(없으면 실패). `--only hero,st-ctrl`: 일부만.
- `--out PATH --clean-img`, `--jobs N`(기본 4).

`.cache/`, `out/`, `out_*/`는 생성물(Git 제외). 배포: `index.html,img/,models/,vendor/,assembly.json,JS/CSS` 복사. 게시 저장소=`zzskm.github.io/keyboard-46es/`(이 저장소 커밋만으로 게시 갱신 아님).

## spec

`groups`=CAD 바디 패턴+`@그룹`. `renders`=표시/카메라/단면. 본문 토큰 `{{p:}} {{v:}} {{d:}} {{n:}}`. yaw 0=−Y(앞), −π/2=+X. 조립 단계 ID/구매품 ID는 체크·진행 기록에 쓰이므로 변경 금지. 3D 단계는 `assembly_v5.json`(`show,focus,needs,view,hardwareStages`). 배선은 3D 형상 없음, 케이스/하드웨어/키캡은 참고. `assets/vendor/`=Three.js 0.180.0+MIT(오프라인). 3D 뷰어는 버튼 클릭 시 로드.

## 비교/검토/검증

`comparison_r2.json`=DWG 판 윤곽·두께·배치 가정(공칭/가정). `model/reference_r2/` STEP/STL. 갱신: `python 46es/tools/build_r2_reference.py`(CadQuery 2.6, ezdxf).

SolidCraft 없는 UI 검토: `python 46es/guide/preview_from_published.py --published <v5 자산 폴더>`(`assembly.json,models/,img/`, 해시 일치, Pillow). 정식 빌드 대체 아님.

검증: `python -B 46es/tools/check_repository.py`(경로/참조, CAD 재평가·브라우저 아님). 브라우저: `46es/`에서 `python guide/check_browser.py`(Playwright, 서버 필요, `BROWSER_EXECUTABLE/GUIDE_URL/GUIDE_SHOT_PREFIX`).
