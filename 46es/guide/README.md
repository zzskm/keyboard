# 46es 설계 검토·조립 가이드 생성기

`guide_v3.json`(내용)과 CAD 모델에서 정적 웹페이지 한 장(`index.html` + `img/`)을 만든다. 게시본은 <https://zzskm.github.io/keyboard-46es/>이다.

## 무엇이 자동이고 무엇을 손으로 쓰나

| 자동(모델·CSV에서) | 손으로(`guide_v3.json`) |
|---|---|
| 렌더 PNG. 단계마다 보일 바디, 카메라, 단면을 spec에 적으면 `solidcraft-cli snapshot`으로 찍는다 | 조립 단계 문장, 확인할 것, 안 맞을 때 대처 |
| 출력 부품 표의 부피와 X×Y×Z(`solidcraft-cli eval`), JLC 최소 크기 경고 | 맞춤 검토 표, 열린 항목, 구매품, 국부 시험, 결정 기록 |
| 상단 칩의 실측 개수와 모델 바디·오류 수, 실측 카드(`model/measurements.csv`) | 실측 카드의 짧은 이름과 표시 문구(`names`, `pills`) |
| 문장 속 숫자 토큰: `{{p:매개변수}}`, `{{v:바디}}`(cm³), `{{d:바디}}`(크기), `{{n:패턴}}`(바디 수) | |
| 푸터의 모델 이름·SHA-256·피처·스케치·오류 수와 생성일 | |

모델이 바뀌면 다시 돌리기만 하면 렌더, 부품 표, 토큰 숫자가 따라온다. 바디 이름이 바뀌어 spec의 패턴이 아무 바디도 못 찾으면 빌드가 멈추고 그 패턴을 알려 준다.

## 실행

SolidCraft가 설치돼 있어야 한다(`C:\Program Files\SolidCraft\solidcraft-cli.exe`, 다르면 `--cli`).

```
cd 46es/guide
python build_guide.py                         # → out/index.html, out/img/
python build_guide.py --only hero,st-ctrl     # 이 렌더만 다시, 나머지는 캐시
python build_guide.py --skip-renders          # 문장만 고쳤을 때(캐시 없으면 실패)
python build_guide.py --out D:/work/zzskm.github.io/keyboard-46es --clean-img   # 게시 폴더로
```

- 렌더 한 장은 모델을 열어 약 27초 걸린다. 기본 4장씩 병렬(`--jobs`)이라 전체 13장이 약 4분이다.
- 결과는 `.cache/`에 모델 해시와 렌더 설정 키로 저장된다. 문장만 바꾸면 몇 초, 모델이 바뀌면 전부 다시 찍는다. `.cache/`와 `out/`은 git에 넣지 않는다.
- `--clean-img`는 출력 폴더의 `img/`에서 이번 빌드가 쓰지 않는 PNG를 지운다.

## 게시

```
cd D:/work/zzskm.github.io && git pull --ff-only
python D:/work/keyboard/46es/guide/build_guide.py --out D:/work/zzskm.github.io/keyboard-46es --clean-img
git add keyboard-46es && git commit -m "docs(keyboard-46es): 가이드 재생성" && git pull --rebase && git push
```

Pages 저장소에는 자동 커밋이 계속 쌓이므로 커밋 전에 `pull --ff-only`, push 전에 `pull --rebase`를 한다.

## spec 구조 (`guide_v3.json`)

- `model`, `measurements`: spec 기준 상대 경로.
- `cameras`: `{target, yaw, pitch, distance, fov}`(mm, 라디안). yaw 0은 −Y(앞)에서, **yaw −π/2는 +X 쪽에서** 본다. pitch +π/2는 위에서 본 평면도.
- `groups`: 바디 이름 패턴(`*` 와일드카드) 묶음. 다른 묶음은 `@이름`으로 참조한다.
- `renders`: `{id, show, hide?, camera?, size?, section?, style?}`.
  - `section`은 CLI `--section` 값이다. `x=6.494`는 작은 쪽을 남기고, `,flip`을 붙이면 큰 쪽을 남긴다.
  - `style`은 `{body, opacity, color}`로 반투명·색을 지정한다.
- `page`: 제목, 칩(`{"auto":"measurements"}`, `{"auto":"model"}` 또는 `{tone, text}`), 범례, 대표 렌더.
- `sections`: 순서대로 쓰인다. `type`은 `summary`, `structure`, `fit`, `issues`, `parts`, `assembly`, `steps`, `table`, `measurements`, `log` 중 하나다. 체크박스 id는 `issues[].id`와 `assembly…steps[].id`에서 오므로, 바꾸면 보는 사람의 체크 기록이 끊긴다.

문장 필드에는 HTML을 쓸 수 있다(`<b>`, `<code>`, `<small>`). spec은 저장소 작성자만 고치는 신뢰 입력이다.
