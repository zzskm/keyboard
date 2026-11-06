# 46es — PSD60용 46키 hand-wired 키보드

**현행 설계는 v5다.** non-split 키보드이며 plate만 제작·조립을 위해 좌우로 나뉜다. 46sp는 별도 참고 키보드다. 현재 상태는 **시험 출력 전**이며 실물 적합성 검증은 남아 있다.

| 목적 | 기준 자료 |
|---|---|
| 작업 절차·변경 검증 기준 | [작업 지침](AGENTS.md) |
| 현재 구조·치수·결정 이유 | [설계 기준](docs/design.md) |
| 제작 파일·재료·수량·시험 순서 | [v5 제작 세트](model/print_v5/README.md) — 주문 1 시험 → 통과 후 주문 2 |
| 미확인 항목·검증·재생성 | [검증과 다음 작업](docs/validation.md) |
| 조립 과정 | [게시 가이드](https://zzskm.github.io/keyboard-46es/) · [가이드 생성 방법](guide/README.md) |
| 편집 CAD·파생 파일·비교 기준 | [모델 안내](model/README.md) |
| 실측 기록 | [측정 자료](model/measurements/README.md) |
| 키맵 | [펌웨어 JSON](firmware/46es_kbfirmware.json) |
| 원본 근거 | [아크릴 r2 DWG](cad/46es_r2_keyboard.dwg) · [판독 보고서](inspection/46es_r2_dwg_inspection.md) |

다음 작업은 주문 1 쿠폰·mount 시험과 케이스 폭·키캡 높이 확인이다. 시험 결과를 반영한 뒤 v5 CAD, 출력물, 가이드를 함께 갱신한다.

## 파일 유지 기준

현재 입력, 사용 중인 출력물, 검증 기준, 원본 근거만 유지한다. 텍스트 파일도 같은 기준을 적용한다. 끝난 작업 로그·폐기안·중복 사본은 추가하지 않는다. 이전 버전은 [정리 전 Git 이력](https://github.com/zzskm/keyboard/tree/72d3ea1ea8939ef29bc34afd62b5b2a4978f19a6/46es)에서 찾는다.

`model/baselines/`의 두 CAD는 현행 생성·검증 입력이므로 남긴다. 나머지 구버전과 `.bak`는 보관 폴더로 옮기지 않는다. `manifest.json`은 Git index의 추적 파일 목록이며 설계 승인 상태를 뜻하지 않는다.

저장소 루트에서 변경을 stage한 뒤 검사한다:

```sh
git add 46es
python -I 46es/tools/update_manifest.py
git add 46es/manifest.json
python -I 46es/tools/update_manifest.py --check
python -B 46es/tools/check_repository.py
```
