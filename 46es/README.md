# 46es — PSD60용 46키 hand-wired 키보드

**현행 설계 v5**, non-split. plate만 제작/조립을 위해 좌우 분할. 46sp는 별도 참고. 상태: **시험 출력 전**(실물 검증 필요).

## SOT

- **편집 원본:** `tools/build_seam_v5.py`
- **생성 CAD(직접 편집 금지):** `model/46es_mount_seam_v5.sc` 등
- **회귀 기준( SOT 아님):** `model/baselines/`
- **구분:** `model/46es_assembly_review_v5.sc`=조립 검토, `model/print_v5/`=제작 세트(STEP은 조립 좌표)

| 목적 | 문서 |
|---|---|
| 작업 절차 | [AGENTS.md](AGENTS.md) |
| 구조·치수·결정 | [docs/design.md](docs/design.md) |
| 제작/시험(주문1→2) | [model/print_v5/README.md](model/print_v5/README.md) |
| 미확인·재생성·검증 | [docs/validation.md](docs/validation.md) |
| 조립 | [게시 가이드](https://zzskm.github.io/keyboard-46es/) · [guide/README.md](guide/README.md) |
| 모델/보존 변형 | [model/README.md](model/README.md) |
| 실측 | [model/measurements/README.md](model/measurements/README.md) |
| 키맵/원본 근거 | [firmware/46es_kbfirmware.json](firmware/46es_kbfirmware.json) · [cad/46es_r2_keyboard.dwg](cad/46es_r2_keyboard.dwg) · [inspection/46es_r2_dwg_inspection.md](inspection/46es_r2_dwg_inspection.md) |

다음 작업: 주문 1 쿠폰·mount 시험, 케이스 폭·키캡 높이 확인 → v5 CAD/출력물/가이드 반영.

## 유지/검사

현재 입력·사용 출력물·검증 기준·원본 근거만 유지. 이전 버전은 태그 `46es-pre-cleanup-2026-11-06`([정리 전 Git 이력](https://github.com/zzskm/keyboard/tree/72d3ea1ea8939ef29bc34afd62b5b2a4978f19a6/46es)) 참조. 결정을 바꾼 경위는 [design.md 결정 이력](docs/design.md#결정-이력).

```sh
python -B 46es/tools/check_repository.py
```
