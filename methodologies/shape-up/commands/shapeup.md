# /shapeup — Shape Up Command

Pitch 작성부터 Betting Table, 사이클 Hill Chart까지 Shape Up 워크플로우를 관리합니다.

## Usage

```
/shapeup pitch new <title> [--appetite|-a small-batch|big-batch]
/shapeup pitch list [--state|-s <state>]
/shapeup pitch show <PCH-ID>
/shapeup pitch ready <PCH-ID>    # 베팅 테이블 준비 완료
/shapeup pitch not-bet <PCH-ID>  # 이번 사이클 기각

/shapeup bet <PCH-ID> [--cycle|-c <cycle>] [--by|-b <who>] [--rationale|-r <reason>]
/shapeup not-bet <PCH-ID>

/shapeup hill new [--cycle|-c <cycle-id>]   # Hill Chart 스냅샷 생성
/shapeup hill show <HLC-ID>                 # ASCII 시각화
```

## Shape Up 핵심 개념

| 개념 | 설명 |
|------|------|
| **Appetite** | 이 아이디어에 얼마나 투자할지 — *먼저 결정*, 추정이 아님 |
| **Small Batch** | 1~2주, 소규모 팀 |
| **Big Batch** | 6주, 사이클 전체 투입 |
| **Pitch** | 문제 + appetite + 해결 방향 (세부 디자인 아님) |
| **Betting Table** | 다음 사이클에 어떤 pitch를 build할지 결정하는 회의 |
| **Circuit Breaker** | appetite 초과 시 자동 종료 — 연장 없음 |
| **Hill Chart** | 작업 진행 상태 시각화 (불확실 → 확실) |
| **Cool-down** | 사이클 사이 2주 — 자유 작업, 기술 부채, 다음 shaping |

## Workflow

```
[Cool-down: Shaping]
1. /shapeup pitch new "주문 알림 재설계" --appetite big-batch
2. # pitch YAML 편집 — Problem, Solution, Rabbit Holes, No-Gos 작성
3. /shapeup pitch ready PCH-20260501-001

[Betting Table]
4. /shapeup pitch list --state ready   # 후보 목록
5. /shapeup bet PCH-20260501-001 --cycle "2026-Q2-C1" --by "CEO" --rationale "가장 높은 retention 임팩트"
6. /shapeup not-bet PCH-20260501-002   # 이번 사이클 기각 (다음에 재심)

[Building]
7. /shapeup hill new --cycle "2026-Q2-C1"
8. # hill YAML 편집 — 각 scope의 위치 기록
9. /shapeup hill show HLC-20260501-001
```

## Pitch States

```
shaping → ready → bet → building → done
                      ↘ not-bet (이번 사이클 기각, 재pitch 가능)
                                 ↘ abandoned (영구 기각)
```

## Hill Chart 읽기

```
  Uphill (불확실)     [HILLTOP]     Downhill (실행 중)
  0%    25%    50%    50%    75%    100%
  |------|------|------|------|------|
  ●                                    "결제 UI 재설계"  ← 막 시작
         ●                             "API 연동"        ← 탐색 중
                      ●                "알림 발송 로직"  ← 방향 확정
                             ●         "E2E 테스트"      ← 마무리 중
```

## Shape Up vs Scrum

| | Shape Up | Scrum |
|--|----------|-------|
| 계획 단위 | 6주 고정 사이클 | 2주 스프린트 |
| 범위 | 가변 (고정 시간에 맞춤) | 고정 (시간이 늘어날 수 있음) |
| 백로그 | 없음 (pitch pool) | 있음 (product backlog) |
| 추정 | 없음 (appetite) | 있음 (story points) |
| 연장 | Circuit Breaker로 금지 | 흔함 |

## Composition

```
/methodology compose shape-up lean-mvp    # Pitch = Hypothesis (검증 가능한 단위)
/methodology compose shape-up rfc-driven  # 큰 pitch는 RFC 먼저
/methodology compose shape-up bdd         # 범위 정의 → 시나리오로 세분화
```
