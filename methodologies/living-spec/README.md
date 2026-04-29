# Living Spec — Methodology Plugin

> 1→N 추가개발 시나리오를 위한 spec evolution 도구

## 목적

기존 Ouroboros가 생성한 `seed-v1`이 있는 프로젝트에 **추가 요구사항**이 들어왔을 때:

1. `/interview` 다시 돌려 새 요구사항 캡처
2. `/seed` — 자동으로 `seed-v2.yaml` 생성 (Ouroboros의 기본 동작)
3. **`/diff-spec`** — v1 ↔ v2 의미 단위 비교
4. **`/migrate-tasks`** — 기존 decompose 태스크들의 영향 분석
5. `/decompose --new-only` 로 추가 태스크만 생성 (v0.2)
6. `/run` → 신규/수정 태스크만 진행

Living Spec은 단계 3·4를 추가하는 메서드이며, 1·2·5·6은 Ouroboros 그대로 사용.

## 활성화

```
/methodology compose ouroboros living-spec
```

조건: `.harness/ouroboros/seeds/seed-v1.yaml` 이상이 존재해야 함.

## 제공 명령

| 명령 | 역할 |
|------|------|
| `/diff-spec` | seed-vN ↔ seed-v(N+1) 의미 단위 diff. 변경된 AC·엔티티·액션·제약·아키텍처 |
| `/migrate-tasks` | 기존 태스크 분류: unchanged / modified / deprecated / added |

## 추가되는 게이트

| 게이트 | 역할 | 강도 |
|-------|-----|-----|
| `check-spec-drift.sh` | 코드에 있는 엔티티가 현 seed에 누락됐는지 휴리스틱 검사 | warning (v0.1은 best-effort, 활성화는 `HARNESS_SPEC_DRIFT_VERBOSE=1`) |

## 디렉토리 산출물

```
.harness/ouroboros/seeds/.diffs/
  └── diff-v1-to-v2.md                    ← /diff-spec 결과

.harness/ouroboros/tasks/migration-plans/
  └── migration-v1-to-v2.yaml             ← /migrate-tasks 결과
```

## 시나리오 예시

**외주 백오피스에 "결제 부분환불" 기능 추가**

```bash
# 1. 새 요구사항 인터뷰
/interview "결제 부분환불 기능 추가"

# 2. seed-v2 생성 (자동 — 기존 seed-v1 위에 evolve)
/seed

# 3. v1 → v2 변경 사항 확인
/diff-spec
# → diff-v1-to-v2.md
#    Added AC: AC-019 (부분환불 처리)
#    Modified Entity: Refund.amount (decimal → enum)  ← 🔴 breaking
#    Added Action: Order.partial_refund

# 4. 기존 태스크 영향 분석
/migrate-tasks --to 2
# → migration-v1-to-v2.yaml
#    Total: 12 tasks
#    Unchanged: 9
#    Deprecated: 1 (TASK-007 — 전체환불 로직, Refund.amount 제거됨)
#    Added: 3 (새 AC-019 + 액션 1 + 엔티티 1 커버 필요)

# 5. 신규 태스크만 생성
/decompose --new-only       # (Phase 1 enhancement)

# 6. 신규/수정 태스크 실행
/run
```

## 한계 (v0.1)

- `modified` 분류 미구현 — 현재 (deprecated가 아니면) 모두 unchanged 처리. v0.2에서 AC description 변경/엔티티 필드 변경 감지 추가 예정
- `check-spec-drift.sh` 휴리스틱 noise 많아 silent (verbose 모드만)
- LLM-assisted semantic match 미구현 (v0.3)
- `task.references` 블록이 없는 태스크는 unchanged로 간주 — 기존 `/decompose`가 이 블록을 채워야 함

## 진화 계획

| 버전 | 추가 사항 |
|-----|---------|
| v0.1 (현재) | diff-spec, migrate-tasks (deprecated/added만), spec-drift 게이트 (silent) |
| v0.2 | modified 분류, /decompose --new-only, spec-drift 게이트 활성화 |
| v0.3 | LLM-assisted semantic match, 자동 review queue |

## Parallel Change와 조합

`/diff-spec`이 breaking-change indicator를 띄우면:

```
/methodology compose ouroboros living-spec parallel-change
```

이러면 expand → migrate → contract 워크플로우가 더 추가됨. Living Spec은 "무엇이 바뀌었는지", Parallel Change는 "어떻게 안전하게 바꿀지"를 담당.
