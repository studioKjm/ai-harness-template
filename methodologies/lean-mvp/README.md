# Lean MVP — Methodology Plugin

> Build → Measure → Learn — 가설 기반 기능 검증. 피벗 or 지속.

## 목적

기능을 풀로 구현하기 전 **최소 가설**을 세우고, MVP를 빠르게 출시, **하나의 지표**로 검증 후 피벗/지속/폐기를 결정.

```
[아이디어]
    ↓
/lean new --title <name> --metric <metric> --target <threshold>  — 가설 정의 (💡 proposed)
    ↓
MVP 구현 (최소한의 기능)
    ↓
/lean build <id>        — MVP 출시 (🔨 testing)
    ↓
측정 기간 (default 14일)
    ↓
/lean measure <id> --actual <value>    — 데이터 수집 (📏 measuring)
    ↓
/lean decide <id> persist|pivot|abandon  — 결정 (✅ decided)
```

## 활성화

```bash
/methodology use lean-mvp
```

requires: 없음. 단독 또는 ouroboros/tdd-strict와 조합.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/lean new` | 새 가설 정의 |
| `/lean build` | MVP 출시 (proposed → testing) |
| `/lean measure` | 측정 기록 (testing → measuring) |
| `/lean decide` | 피벗/지속/폐기 결정 (measuring → decided) |
| `/lean status` | 가설 상태 확인 |
| `/lean list` | 전체 가설 목록 |

## 가설 구조

```
"We believe that {action} will result in {outcome} for {user}"
```

**하나의 지표 원칙**: 성공/실패를 판단할 단 하나의 숫자만 추적.

## 상태 기계

```
💡 proposed → 🔨 testing → 📏 measuring → ✅ decided
                                              (persist | pivot | abandon)
```

**pivot** 결정 시 새 가설 자동 체인 연결 (`--next-hyp`).

## 산출물

```
.harness/lean-mvp/
├── hypotheses/hyp-YYYYMMDD-NNN.yaml  # 가설별 상태+데이터
└── config.yaml                        # 프로젝트 설정
.harness/state/lean-mvp.yaml
```

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ ouroboros` | 가설 → 시드 스펙 → 구현 → 검증 |
| `+ tdd-strict` | MVP 구현 시 TDD 사이클 |
| `+ observability-first` | SLO 지표를 가설 metric으로 연결 |
| `+ rfc-driven` | 대형 실험은 RFC 선행 |

## 안티패턴

- ❌ **여러 지표 동시 추적** — 하나가 성공하면 성공으로 볼 것인지 불명확
- ❌ **MVP가 풀 기능** — "MVP"가 6주 개발이면 Lean이 아님
- ❌ **측정 기간 무제한** — deadline 없으면 결정이 늦어짐
- ❌ **데이터 없이 decide** — `metric_actual` 없으면 결정 불가
- ❌ **pivot을 실패로 인식** — pivot은 학습 사이클의 완성
