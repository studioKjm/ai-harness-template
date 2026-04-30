# Observability First — Methodology Plugin

> 메트릭·로그·트레이스·SLO를 스토리 작성 시점에 정의. 사후 retrofit 금지.

## 목적

MVP에서 가장 자주 스킵되는 영역:
- 배포 후 "왜 느리지?" — 측정값 없음
- "이 기능 쓰이고 있나?" — 메트릭 없음
- "장애 났는데 어디서?" — 트레이스 없음

→ **observability-first는 스토리 작성 시점에 텔레메트리를 설계 산출물로 만듦**.

## 활성화

```bash
/methodology compose ouroboros bmad-lite observability-first
# 또는 단독 (기존 코드의 텔레메트리 audit)
/methodology use observability-first
```

prerequisites: 없음.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/observe define <slug>` | 신규 spec (story/feature/endpoint/module 대상) |
| `/observe add-metric <id>` | 메트릭 추가 (counter/gauge/histogram/summary) |
| `/observe add-log <id>` | 로그 이벤트 추가 (level + 필드 + PII 마킹) |
| `/observe coverage <id>` | 커버리지 마킹 (files/symbols) |
| `/observe instrument <id>` | defined → instrumented (커버리지 검증) |
| `/observe measure <id>` | instrumented → measuring (production 데이터 흐름) |
| `/observe-slo new <slug>` | SLO 정의 (SLI + target + window) |
| `/observe-slo activate <id>` | proposed → active (alert 활성화) |
| `/observe-slo record-violation <id>` | SLO 위반 기록 (incident 연결) |
| `/observe list-specs / show-spec` | 목록 / 상세 |
| `/observe-slo list / show / retire` | SLO 관리 |

## State Machine

**Spec**:
```
[draft] → [defined] → [instrumented] → [measuring] → [review-due] → [measuring]
```
(measuring 90일 후 자동으로 review-due 마킹, 검토 후 measuring 복귀)

**SLO**:
```
[proposed] → [active] → [retired]
```

## 추가되는 게이트

| 게이트 | severity | 역할 |
|-------|---------|------|
| `check-observability-coverage.sh` | warning | 1) Logic 레이어 파일 중 spec 없는 것, 2) measuring >90d 미검토 spec |

Logic 레이어 휴리스틱 디렉토리 (자동 감지):
- `src/services/`, `src/logic/`, `src/usecases/`, `src/domain/`, `src/core/`
- `app/services/`, `app/usecases/`
- `lib/services/`

## 메트릭 타입 가이드

| 타입 | 용도 | 예시 |
|-----|-----|-----|
| counter | 이벤트 카운트 (단조증가) | `request_total`, `errors_total` |
| gauge | 시점값 (오르내림) | `active_connections`, `queue_depth` |
| histogram | 분포 측정 | `request_duration_ms`, `payload_size_bytes` |
| summary | 사전 계산 quantile | (대부분 histogram이 더 나음) |

각 메트릭은 `--question`(어떤 질문에 답하는가) 필수 — 답 못하면 제거.

## SLO 작성 가이드

**SLI (Service Level Indicator)** = `good_events / valid_events`

```yaml
sli:
  good_events:  'sum(rate(refund_request_total{status_code!~"5.."}[5m]))'
  valid_events: 'sum(rate(refund_request_total[5m]))'

target:
  percentage: 99.5      # 99.5% 의 요청이 5xx 없이 성공
  window: "30d"

error_budget:
  per_window: "0.5%"
  in_minutes: 216       # 99.5% over 30d ≈ 216분 다운타임 허용
```

**Burn rate alert**:
- `14x` (1h window) → page on-call (예산 1/14 시간에 소진 페이스)
- `6x` (6h window) → ticket

**SLO target 기준**:
| Target | 적합한 곳 |
|-------|---------|
| 99% | 내부 도구 |
| 99.5% | 일반 API |
| 99.9% | 사용자 핵심 서비스 |
| 99.99% | 결제·인증·인프라 critical |
| 100% | ❌ 절대 금지 (변경 여유 0) |

## 산출물

```
.harness/observability-first/
├── specs/
│   └── obs-2026-04-30-refund-api.yaml   # metrics/logs/traces + 커버리지
└── slos/
    └── slo-refund-availability.yaml     # SLI + target + burn rate alert
```

## 시나리오 예시

**Refund API 신규 — 텔레메트리 설계부터**

```bash
# 0. 가정: 스토리 st-2026-04-30-refund 작성됨

# 1. spec 정의
/observe define refund-api \
  --target-kind story \
  --target-ref st-2026-04-30-refund \
  --description "Refund API observability"

# 2. 메트릭 추가
/observe add-metric obs-2026-04-30-refund-api \
  --name "refund_request_total" \
  --type counter \
  --labels method status_code merchant_id \
  --question "How many refund requests, segmented by outcome?"

/observe add-metric obs-2026-04-30-refund-api \
  --name "refund_processing_duration_ms" \
  --type histogram \
  --labels merchant_id \
  --question "Distribution of refund processing time" \
  --unit ms

# 3. 로그 이벤트 추가
/observe add-log obs-2026-04-30-refund-api \
  --event "refund.requested" --level info \
  --field merchant_id --field amount --field "user_id:pii"

/observe add-log obs-2026-04-30-refund-api \
  --event "refund.failed" --level error \
  --field merchant_id --field reason_code --field underlying_error

# 4. SLO 정의
/observe-slo new refund-availability \
  --service billing-api \
  --sli-good 'sum(rate(refund_request_total{status_code!~"5.."}[5m]))' \
  --sli-valid 'sum(rate(refund_request_total[5m]))' \
  --target 99.5 \
  --window 30d

# 5. 코드 작성 후 커버리지 마킹
/observe coverage obs-2026-04-30-refund-api \
  --files src/billing/refund.ts src/billing/refund-handler.ts \
  --symbols "RefundService.process" "POST /api/refunds"

# 6. 검증 → instrument
/observe instrument obs-2026-04-30-refund-api

# 7. 배포 후 데이터 확인 → measure
/observe measure obs-2026-04-30-refund-api

# 8. SLO 활성화 (alert·dashboard 준비 후)
/observe-slo activate slo-refund-availability

# 9. 장애 발생 시 SLO 위반 기록
/observe-slo record-violation slo-refund-availability \
  --duration 45 --burn-rate 18 \
  --incident-id inc-2026-04-30-billing-outage
```

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ ouroboros` | SLO target이 시드 AC ("system MUST achieve 99.5%") |
| `+ bmad-lite` | story에 performance/availability AC 있으면 spec 자동 요구 |
| `+ incident-review` | 위반 기록이 incident와 연결, 패턴 분석 보강 |
| `+ exploration` | observability 비용·실현가능성 spike → 학습 |
| `+ parallel-change` | 새 모듈 spec이 legacy의 SLO 패리티 검증 |
| `+ strangler-fig` | facade가 라우팅 결정 메트릭 emit |
| `+ threat-model-lite` | 보안 위협 탐지 메트릭 (실패한 인증 시도, IDOR 의심 등) |

## 안티패턴

- ❌ **메트릭에 user_id/request_id 라벨** — 카디널리티 폭발. 로그 필드로
- ❌ **info 레벨 남발** — 신호가 잡음에 묻힘
- ❌ **target 100%** — error budget 0, 어떤 변경도 위반
- ❌ **alert 없는 SLO** — 측정만 하고 행동 안 함
- ❌ **runbook 없는 alert** — 호출 받아도 뭐 할지 모름
- ❌ **장애 후 메트릭 추가** — 정의상 observability-first가 아님

## 한계 (v0.1)

- 자동 텔레메트리 합성 없음 (코드 자동 생성 미지원)
- SLO `recent.*` 필드는 수동 (auto-sync는 v0.2)
- 게이트의 Logic 레이어 감지는 휴리스틱 (디렉토리 컨벤션 의존)
- High-cardinality 경고는 라벨 이름 기반 (실제 카디널리티 미측정)

## 진화 계획

| 버전 | 추가 |
|-----|------|
| v0.1 (현재) | spec/SLO state machine, 메트릭/로그 추가, 커버리지 게이트, 위반 기록 |
| v0.2 | Datadog/Prometheus 연동 (recent 자동 sync), 자동 instrumentation 코드 스니펫 생성 |
| v0.3 | LLM 기반 메트릭 추천 (코드 분석), SLO 추천 (incident 패턴 기반) |
