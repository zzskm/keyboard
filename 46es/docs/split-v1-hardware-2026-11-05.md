# 46es split v1 구매 후보와 체결 스택

기준일: 2026-11-05 KST. **CAD 검토 후보 / 발주하지 않음.** 국내 재고·배송·가격·MOQ는 확인하지 않았다.

| 위치 | 구매 후보 | 수량 | CAD 반영 |
|---|---|---:|---|
| SO1–6 지지대 | Harwin R30-1000602, M3 암–암 관통, 길이6mm, AF5, 황동/니켈 | 6 | 육각 AF5, 관통Ø3 단순화, Z2–8 |
| Plate 위 | Würth 00600134 또는 동등품, ISO7380-1 M3×4, 자석에 붙는 탄소강 | 6 | 나사Ø3×4, 머리 포락Ø5.7/H1.65 |
| Mount 아래 | Würth 00600135 또는 동등품, ISO7380-1 M3×5 탄소강 | 6 | 나사Ø3×5, 같은 머리 포락 |
| Bracket↔plate2곳 + spine↔plate4곳 | NBK SSH-M2-6 저두 | 6 | Ø4/H1.1 머리, 와셔 없음 |
| Mount 앞/뒤 lap 각2곳 + gate1곳 | NBK SSH-M2-5 저두 | 5 | 동일 머리, 와셔 없음 |
| M2 너트 | DIN934 M2, AF4/H1.6, 강철 | 11 | 포켓 AF4.4/깊이1.8, 참조 너트 AF4/H1.6 |
| Cover 자석 | Ø4×2 네오디뮴 후보, 기존 보스 포켓 사용 | 6 | 기존 포켓Ø4.2/깊이2.1 유지, 실제 흡착력/접착 미검증 |
| 중앙 shim | 절연성 박판, 국부 받침 크기에 맞춤 | 시험분 | 현재 공칭 틈0.05mm에 현물 맞춤;0–0.1mm 조정 목표 |

보유 M3×5 둥근머리는 실제 머리Ø/높이가 위 포락 안에 들 때만 대체한다. 형상이 다르면 새 구매 후보를 사용한다. M3×8 평머리와 M3×5×4 인서트는 이번 구조에 억지로 사용하지 않는다. 재고 M3 암–암5mm 지지대의 **꼭짓점 외경5mm → AF4.330127mm**는 새 AF5 후보와 다르다. M1.6×14의 용도는 미정이며 케이스 나사로 지정하지 않았다.

## 공칭 체결 스택

| 체결 | 머리 받침 / 나사 끝 Z | 너트·지지대 | 물림 및 잔여 |
|---|---|---|---|
| M3 위×4 | 받침9.5 / 끝5.5 | 지지대2–8 | 물림2.5mm, 약5피치 |
| M3 아래×5 | 받침0 / 끝5 | 지지대2–8 | 물림3mm, 약6피치; 위 나사와 끝 간격0.5 |
| M2 bracket×6 | 받침10.2 / 끝4.2 | 너트4.6–6.2 | 공칭 너트1.6 전체 통과 + 아래0.4; PCB 점유 상단3.9와 끝 간격0.3 |
| M2 spine×6 | 받침10.2 / 끝4.2 | 너트5.2–6.8 | 너트 전체 통과 + 아래1.0; 실제 배선 경로 확인 필요 |
| M2 lap×5 | 받침1.7 / 끝−3.3 | 너트−2.8–−1.2 | 전체 통과 + 아래0.5; tongue 하면−3보다0.3 돌출 |
| M2 gate×5 | 받침4.8 / 끝9.8(위로) | 너트7.8–9.4 | 전체 통과 + 위0.4; plate 포켓 천장10까지0.2 |

M3 위 머리 상단11.15와 자석 하단11.6 사이0.45mm. Ø6 카운터보어 안의 반경 여유0.15mm는 FDM 보장 공차가 아니다. 육각 지지대 포켓 AF5.4는 면당0.2mm 후보다. SO3 회피는 꼭짓점 기준 공칭 반경0.513mm다.

나사산은 참조 원통으로 단순화했다. 실제 나사 끝/챔퍼/불완전산과 지지대 양 끝 챔퍼를 뺀 유효 물림은 감소할 수 있다. 특히 위 M3의2.5mm 물림은 강도 검증이 아니다. 손 조립·반복 탈착·중앙 처짐·나사 끝 간격을 국부 시험에서 확인한 뒤 채택한다. 제조사 금속 조합용 토크를 FDM 플라스틱에 그대로 적용하지 않는다.

## 확인한 공급 자료

- [Harwin R30-1000602](https://www.harwin.com/products/R30-1000602): M3 through-threaded female-female,6mm,5mm AF. 막힌 양끝 탭 지지대와 대체하지 않는다.
- [Würth M3×4 / 00600134](https://eshop.wuerth.de/Screw-with-flattened-half-round-head-and-hexagon-socket-ISO-7380-1-steel-0109-zinc-plated-blue-passivated-A2K-SCR-ISO7380-1-0109-HS2-A2K-M3X4/00600134.sku/en/US/EUR/).
- [Würth M3×5 / 00600135](https://eshop.wuerth.de/Schraube-abgeflachter-Halbrundkopf-und-Innensechskant-ISO-7380-1-Stahl-0109-verzinkt-blau-passiviert-A2K-SHR-ISO7380-1-0109-IS2-A2K-M3X5/00600135.sku/de/DE/EUR/): steel,Ø5.7/H1.65.
- [Böllhoff ISO7380-1 도면](https://eshop-ro.boellhoff.com/out/media/pdf/ISO_7380-1_Stahl_10.9_Innensechskant___en.pdf): M3 머리 포락 근거.
- [NBK SSH 공식 표](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/socketheadcapscrew/SSH/): M2×4/5/6/8 카탈로그 규격. M2 머리Ø4/H1.1, 육각 공구1.3mm. 이번 모델은×5/×6을 사용한다.
- [Fastenright DIN934 micro full nut](https://www.fastenright.com/general-fixings/micro-hexagon-fullnuts-din-934/mf06): M2 AF4/H1.6.

## 갱신 기록

- 2026-11-05: 규격·공칭 물림과 CAD 참조 일치 확인. 구매처/물성/실제 치수/최종 체결 승인 보류.
