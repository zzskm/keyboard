# v5 조립 가이드 생성기

`guide_v5.json`(설명) + `assembly_v5.json`(3D 단계) + `model/46es_assembly_review_v5.sc`에서 정적 웹 가이드를 만든다. [게시본](https://zzskm.github.io/keyboard-46es/)은 v5다. 이전 게시본 `/v4/`는 별도 Pages 저장소의 기록이며 현재 생성 대상이 아니다.

설명·재료·구매 수량은 spec, 부피·경계 상자·렌더·본문 숫자 토큰은 CAD에서 얻는다. 실측 상태 표는 `model/measurements.csv`를 읽는다. 검토 CAD가 읽는 실측 원본은 `model/measurements/2026-11-04T111846Z.json`이며 CSV 상태 표와 역할이 다르다. 측정 갱신은 [측정 자료 안내](../model/measurements/README.md)를 따른다.

## 실행 — 저장소 루트

SolidCraft CLI가 필요하다. 기본 경로는 `C:/Program Files/SolidCraft/solidcraft-cli.exe`이며 `--cli`로 바꿀 수 있다.

```sh
python 46es/tools/build_assembly_reference_v5.py
python -B 46es/inspection/scripts/verify_assembly_reference_v5.py
python 46es/guide/build_guide.py
python -m http.server 8766 --bind 127.0.0.1 --directory 46es/guide/out
```

브라우저에서 `http://127.0.0.1:8766/#interactive`를 연다. 원본 CAD·측정 JSON·생성기·검토 CAD 해시가 다르면 빌드가 중단된다.

- `--skip-renders`: 현재 모델·설정의 렌더 캐시 재사용. 캐시가 없으면 실패한다.
- `--only hero,st-ctrl`: 지정 렌더만 생성. 나머지는 유효한 캐시가 필요하다.
- `--out PATH --clean-img`: 해당 폴더로 출력하고 쓰지 않는 PNG 정리.
- `--jobs N`: 렌더 병렬 수. 기본 4.

`.cache/`, `out/`, `out_*/`는 생성물이며 Git에 넣지 않는다. 배포는 출력 폴더 전체(`index.html`, `img/`, `models/`, `vendor/`, `assembly.json`, JS/CSS)를 복사한다. 게시 저장소는 `zzskm.github.io`의 `keyboard-46es/`이며 이 저장소 정리만으로 게시 페이지는 갱신되지 않는다.

## spec 편집

`groups`는 CAD 바디 패턴과 `@그룹` 참조다. 없는 바디 패턴이면 실패한다. `renders`에 표시 바디·카메라·단면을 지정한다. 문장 숫자는 `{{p:매개변수}}`, `{{v:바디}}`, `{{d:바디}}`, `{{n:패턴}}`으로 모델에 연결한다. 카메라 yaw 0은 −Y(앞), yaw −π/2는 +X 방향에서 본다.

조립 단계 ID와 구매품 ID는 체크·진행 기록에 쓰이므로 문구를 다듬을 때 바꾸지 않는다. `assembly_v5.json`의 `show`, `focus`, `needs`, `view`, `hardwareStages`가 3D 단계를 결정한다. 배선은 3D 형상이 없고 케이스·하드웨어·키캡은 참고 형상이다.

`assets/vendor/`에는 Three.js 0.180.0과 MIT 라이선스를 고정했다. 오프라인 빌드가 가능하며 npm/CDN 다운로드가 필요 없다. WebGL 실패 시 참고 이미지와 텍스트를 제공한다.

## 검증

CAD 없이 경로·부품 참조를 확인하려면 `python -B 46es/tools/check_repository.py`를 실행한다. 브라우저 검사는 Python Playwright와 실행 중인 위 서버가 필요하다. `46es/`에서 `python guide/check_browser.py`를 실행한다. `BROWSER_EXECUTABLE`, `GUIDE_URL`, `GUIDE_SHOT_PREFIX`로 환경을 지정한다. 단계 이동·선택·검색·완료 기록 복원·모바일 넘침·3D 실패 대체 화면을 검사한다.
