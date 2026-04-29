# Parallel Change — Methodology Plugin

> Expand → Migrate → Contract — 호환 깨는 변경을 다운타임 0으로

## 목적

DB 스키마 변경, API 시그니처 변경, 함수/타입 breaking change 같이 **이전 버전을 즉시 깨면 안 되는** 변경을 안전하게 처리하는 3단계 상태머신.

```
[old만 존재]
    ↓
expand   — old 그대로 두고 new를 옆에 추가. 둘 다 동작.
    ↓
migrate  — caller를 하나씩 old → new로 전환. 둘 다 여전히 존재.
    ↓
contract — caller가 0이 된 시점에만 진입. 이제 old 제거 가능.
    ↓
[new만 존재]
```

각 단계 전환 시점에 **자동 게이트가 검증** — 임의로 단계 건너뛰거나 잘못된 시점에 제거하면 commit이 차단됨.

## 활성화

```
/methodology compose ouroboros parallel-change
```

또는 Living Spec과 함께:
```
/methodology compose ouroboros living-spec parallel-change
```

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/parallel-change new <id>` | 신규 plan 생성 (phase=expand로 시작) |
| `/parallel-change list` | 모든 plan + 현재 phase 요약 |
| `/parallel-change show <id>` | plan 전체 출력 |
| `/expand <id>` | expand 단계 상태 검증 (caller 카운트) |
| `/migrate-traffic <id>` | expand → migrate 전환 |
| `/contract <id>` | migrate → contract 전환 (caller 0건 강제) |

## 추가되는 게이트 (둘 다 blocking)

| 게이트 | 역할 |
|-------|------|
| `check-parallel-state.sh` | 모든 phase의 신·구 공존 상태 일관성 강제. 위반 시 commit 차단 |
| `check-parallel-callers.sh` | contract 단계에서 old caller 발견 시 commit 차단 |

## 산출물 위치

```
.harness/parallel-change/plans/
├── pc-2026-04-28-refund-amount-enum.yaml    # 단일 plan = 단일 변경
├── pc-2026-05-01-orders-api-v2.yaml
└── ...
```

여러 plan을 동시에 진행 가능. 각각 독립된 상태머신.

## 시나리오 예시

**`Refund.amount: number → enum` 변환 (외주 백오피스)**

```bash
# 1. Living Spec이 이미 breaking change 감지했다고 가정
#    /diff-spec 결과: AmountType enum 추가, Refund.amount 시그니처 변경

# 2. Parallel Change plan 생성
/parallel-change new pc-2026-04-28-refund-amount-enum --title "Refund.amount: number → AmountType enum"

# 3. 구버전 시그니처 등록
python3 .harness/methodologies/parallel-change/scripts/pc.py set-old \
  pc-2026-04-28-refund-amount-enum \
  --symbol "Refund.amount" \
  --pattern 'refund\.amount\b'

# 4. 신버전 코드 작성 (Refund.amount_type 추가)
#    이때 .harness/parallel-change/plans/<id>.yaml 의 phases.current 는 expand

# 5. 신버전 시그니처 등록
python3 .harness/methodologies/parallel-change/scripts/pc.py set-new \
  pc-2026-04-28-refund-amount-enum \
  --symbol "Refund.amount_type" \
  --pattern 'refund\.amount_type\b'

# 6. expand 검증
/expand pc-2026-04-28-refund-amount-enum
# → "Callers of OLD: 12, NEW: 1"  ✅ 정상 expand

# 7. caller 하나씩 마이그레이션 (외부 PR 단위로 진행)
# ... (수일~수주 작업) ...

# 8. caller 0 확인 후 migrate phase로
/migrate-traffic pc-2026-04-28-refund-amount-enum
# → "expand → migrate"

# 9. 마지막 caller까지 전환 후 contract
/contract pc-2026-04-28-refund-amount-enum
# 게이트가 자동으로 caller 0건 검증
# → "migrate → contract"  ✅
# 또는
# → "BLOCKED: 3 caller(s) still reference old"  ❌

# 10. 구버전 코드/스키마 제거 commit
#     check-parallel-callers.sh 가 매 commit마다 0건 강제

# 11. plan done 처리
python3 .harness/methodologies/parallel-change/scripts/pc.py advance \
  pc-2026-04-28-refund-amount-enum done
```

## DB 마이그레이션 매핑

전형적 expand-contract DB 패턴:

| Phase | DB 작업 |
|-------|--------|
| expand | `ALTER TABLE refunds ADD COLUMN amount_type TEXT;` (NULL 허용) |
| migrate | dual-write 코드 + backfill 스크립트 |
| contract | `ALTER TABLE refunds DROP COLUMN amount;` (별도 migration 파일) |

각 단계는 별 마이그레이션 파일로 분리 — contract 단계 마이그레이션은 다른 commit으로.

## 한계 (v0.1)

- caller 카운트 = 정적 grep 기반. 동적 import / reflection 호출은 못 잡음
- 동적 호출이 의심되면 `caller_scan.exclude_files`에 추가하고 사람이 검증
- LLM-assisted 호출 그래프는 v0.2 (`/run-pair`와 통합 예정)

## 진화 계획

| 버전 | 추가 사항 |
|-----|---------|
| v0.1 (현재) | 정적 grep 기반 caller 카운트, 4 phase 상태머신, blocking 게이트 2종 |
| v0.2 | AST 기반 caller 분석, `/run-pair`와의 통합 |
| v0.3 | DB 마이그레이션 자동 생성 (expand/contract 분리), Slack/PR 코멘트 알림 |

## Living Spec과 조합

`/diff-spec` 이 🔴 Breaking-change indicator를 띄우면 자동으로 Parallel Change plan 초안을 제안하는 흐름이 v0.2에서 추가될 예정. 현재는 사용자가 직접 plan을 만들어야 함.
