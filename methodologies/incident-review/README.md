# Incident Review — Methodology Plugin

> Blameless postmortem capture — incidents become durable, searchable artifacts.

## 목적

Production 장애가 Slack에서 "고쳤다" 한 줄로 끝나면 같은 문제가 반복됨. incident-review는:

- **timeline + impact + root cause + action items**를 구조화된 yaml로 기록
- **blameless 형식** — 사람이 아니라 시스템에 초점
- **action items 추적** — owner/due/status 강제, overdue는 게이트가 경고
- **패턴 분석** — 분기별 recurring root causes 자동 집계

## exploration과의 차이

| 메서드 | 학습 시점 | 트리거 |
|-------|---------|--------|
| exploration | **선험적** (모르는 걸 알고 시작) | 호기심·미지수 |
| incident-review | **사후적** (예상 못한 문제 발생) | production 장애 |

둘은 **상호 보완** — incident에서 spike가 필요하다고 판단되면 action item을 spike로 변환.

## 활성화

```bash
/methodology compose ouroboros incident-review
# 또는 단독 (긴급 장애 대응만 도입할 때)
/methodology use incident-review
```

prerequisites: 없음. 어느 단계든 사용 가능.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/incident new <slug>` | 신규 incident 기록 시작 |
| `/incident timeline add <id>` | 타임라인 항목 추가 |
| `/incident analyze <id>` | recording → analyzing (RCA 단계) |
| `/incident publish <id>` | analyzing → published (blameless review 통과 후) |
| `/incident close <id>` | published → acted-on (모든 action items 해소) |
| `/incident archive <id>` | acted-on → archived |
| `/incident list / show` | 목록 / 상세 |
| `/incident-action add` | action item 추가 (owner, due, priority 필수) |
| `/incident-action resolve` | action item 해소 (done\|dropped\|converted) |
| `/incident-patterns` | 최근 N일간 recurring root causes 분석 |

## State Machine

```
[recording] → [analyzing] → [published] → [acted-on] → [archived]
```

| 상태 | 의미 |
|-----|-----|
| recording | 타임라인 캡처 중. 대응 진행 또는 막 종료 |
| analyzing | RCA 진행 (5-whys, contributing factors) |
| published | 포스트모템 배포. action items 트래킹 시작 |
| acted-on | 모든 action items 해소 |
| archived | >6개월. 패턴 분석용 보존 |

각 전이는 강제 게이트:
- `analyzing → published`: `blameless_review_passed` + `five_whys.root_cause` 필수
- `published → acted-on`: 모든 action items가 `done | dropped | converted` 상태 (--force 가능, 기록됨)

## Severity 기준

| Sev | 정의 | 응답 |
|-----|-----|-----|
| sev1 | 전체 장애 / 데이터 손실 / 보안 침해 | < 1시간 |
| sev2 | 주요 기능 저하 (subset) | < 4시간 |
| sev3 | 부분 저하 (특정 기능·세그먼트) | 당일 |
| sev4 | 사소함 / 표면 | 익일 |

## 추가되는 게이트

| 게이트 | severity | 역할 |
|-------|---------|------|
| `check-incident-actions.sh` | warning | 1) overdue action items, 2) published 후 0 actions, 3) owner 미지정 action items |

## 산출물

```
.harness/incident-review/
└── incidents/
    └── inc-2026-04-30-billing-outage.yaml   # timeline, 5-whys, action items, history
```

## 시나리오 예시

**Refund API 503 — sev2, 23분 장애**

```bash
# 1. 알림 시점 — incident 생성
/incident new billing-outage \
  --title "Refund API 503 errors for 23 minutes" \
  --severity sev2 \
  --reporter alertmanager

# 2. 대응 중 timeline 캡처
/incident timeline add inc-2026-04-30-billing-outage \
  --time "2026-04-30T14:23:00Z" \
  --event "First 503 from /api/refunds" \
  --source alert

/incident timeline add inc-2026-04-30-billing-outage \
  --time "2026-04-30T14:31:00Z" \
  --event "On-call engineer ack"

/incident timeline add inc-2026-04-30-billing-outage \
  --time "2026-04-30T14:46:00Z" \
  --event "Identified DB connection pool exhausted" \
  --source manual

/incident timeline add inc-2026-04-30-billing-outage \
  --time "2026-04-30T14:48:00Z" \
  --event "Increased pool size, traffic recovered" \
  --source manual

# 3. 대응 종료 — analyze 단계
/incident analyze inc-2026-04-30-billing-outage

# 4. yaml 직접 편집 — 5-whys, contributing factors, impact 채우기
#    (인간 추론 영역, 스크립트가 못 함)
#    started_at: 2026-04-30T14:23Z
#    detected_at: 2026-04-30T14:23Z (동시 — alert)
#    mitigated_at: 2026-04-30T14:48Z
#    duration_minutes: 25
#    five_whys.root_cause: "DB connection pool sized for normal load,
#                           no auto-scaling on traffic spike"

# 5. action items 추가
/incident-action add inc-2026-04-30-billing-outage \
  --description "Add alert when DB connection pool > 80% for 5min" \
  --owner jimin --due 2026-05-15 --priority high

/incident-action add inc-2026-04-30-billing-outage \
  --description "Update billing runbook with this failure mode" \
  --owner jimin --due 2026-05-08 --priority medium

# 6. blameless review 후 publish
#    (yaml 직접 편집: blameless_review_passed: true)
/incident publish inc-2026-04-30-billing-outage

# 7. 후속 작업 진행, action items 해소
/incident-action resolve inc-2026-04-30-billing-outage \
  --action-id ai-1 --status done

/incident-action resolve inc-2026-04-30-billing-outage \
  --action-id ai-2 --status converted --converted-to "ADR-016"

# 8. 모든 actions 해소 후 close
/incident close inc-2026-04-30-billing-outage

# 9. 분기별 패턴 분석
/incident-patterns --days 90
# → "Top recurring root cause: 'DB connection pool exhausted' (3x)"
# → 시스템 투자 결정 근거 확보
```

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ ouroboros` | action item이 task로 변환 (`/decompose`) |
| `+ bmad-lite` | UX 영향 있는 fix는 story로 변환 |
| `+ exploration` | "왜 이런 일이?" 미지수는 spike로 변환 |
| `+ parallel-change` | RCA가 시그니처 변경을 요구하면 plan 생성 |
| `+ strangler-fig` | RCA가 "legacy 모듈이 너무 노후화" → strangler plan |

## 안티패턴

- ❌ **Slack에서 "고쳤다" 한 줄로 끝** — 같은 문제 반복의 근본 원인
- ❌ **action item: "monitoring 개선"** — 모호함. 구체적 alert/metric 명시 필요
- ❌ **owner: 팀** — 책임 분산. 한 사람 지정 (다음 incident에서 rotate 가능)
- ❌ **due: ASAP / 3개월 후** — 비현실적. 1-2주가 적정
- ❌ **5-whys 스킵** — postmortem이 그냥 timeline 기록으로 전락
- ❌ **사람 이름 + 비난 언어** — 학습 문화 파괴. 시스템 관점으로 전환

## 한계 (v0.1)

- timeline 자동 수집 없음 (CloudWatch/Sentry/Slack 연동은 v0.2)
- 패턴 분석은 root_cause 문자열 매치 — 의미적 유사도 미지원 (vocabulary 통일성에 의존)
- action items 트래킹은 incident yaml 안에서만 — 외부 이슈 트래커(Linear/Jira) 동기화 없음
- archived 자동 전환 없음 (수동 명령)

## 진화 계획

| 버전 | 추가 |
|-----|------|
| v0.1 (현재) | 5-state machine, blameless 게이트, 패턴 분석, action items |
| v0.2 | 외부 모니터링 연동 (timeline 자동), Linear/Jira 동기화 |
| v0.3 | LLM 기반 root_cause 의미 매칭, 분기별 자동 retrospective |
