---
description: Crystallize interview results into an IMMUTABLE seed spec (YAML). Run ONLY after /interview reaches ambiguity ≤ 0.2. Extracts ontology, AC, constraints. Once created, seeds cannot be modified — only versioned.
---

# /seed — Seed Specification Generator

> 인터뷰 결과를 불변 스펙으로 결정화한다

## Instructions

You are now the **Seed Architect** agent. Your job is to transform the interview into an immutable specification.

### Phase 0: State Audit (FIRST STEP)

1. **Scan `.harness/ouroboros/seeds/`** — list existing `seed-v*.yaml`
   - If latest seed's goal matches current interview topic → this is a **new version** (e.g., seed-v2 extends seed-v1)
   - If topics differ → fresh seed (seed-v1 of new feature)
2. **Verify latest interview** in `.harness/ouroboros/interviews/` is ≤ 24h old and ambiguity ≤ 0.2
   - If stale or ambiguous → prompt user to run `/interview` again
3. **Check scale** — small feature (1-2 files)? → use `seed-spec-minimal.yaml` template
   - Large feature (multiple layers)? → use full `seed-spec.yaml` template

### Rules
1. 인터뷰 결과가 없으면 먼저 `/interview`를 실행하라고 안내
2. 시드는 한번 생성되면 수정하지 않는다 (새 버전을 만들어야 함)
3. 모든 필드가 채워져야 한다 — TODO나 TBD 금지

### Subagent Delegation

온톨로지 추출의 정확도를 높이기 위해 **subagent를 활용**합니다:

```
1. Subagent(Ontologist) → 인터뷰에서 도메인 모델 추출
   - 엔티티, 관계, 액션을 독립적으로 추출
   - 결과를 메인 에이전트에 반환

2. Main Agent(Seed Architect) → 추출된 온톨로지로 시드 스펙 결정화
```

**Claude Code에서 subagent 사용**:
- 복잡한 인터뷰의 경우 `Agent` 도구로 Ontologist를 별도 spawn하여 온톨로지 추출을 위임
- Ontologist는 `.claude/agents/ontologist.md`의 페르소나를 따름
- 결과를 받아 Seed Architect가 최종 스펙을 조립

### Process

1. **Read** the latest interview from `.harness/ouroboros/interviews/`
2. **Choose template** based on scale (see Phase 0):
   - Minimal (`.harness/ouroboros/templates/seed-spec-minimal.yaml`) — small feature, 1-3 files, single layer
   - Full (`.harness/ouroboros/templates/seed-spec.yaml`) — multi-layer, multi-entity, or complex domain
3. **Delegate** ontology extraction to Ontologist subagent (full mode only; for complex domains)
4. **Extract** ontology (domain model) from answers (full mode)
5. **Crystallize** into seed spec YAML
6. **Validate** all required fields are present
7. **Save** to `.harness/ouroboros/seeds/seed-v{N}.yaml`

### Seed Spec Format

```yaml
# Seed Specification v{N}
# Generated: YYYY-MM-DD
# Source Interview: {interview-file}
# WARNING: This file is immutable. To change, create a new version.

version: {N}
created: "YYYY-MM-DDTHH:MM:SS"
interview_ref: "{interview-file}"

goal:
  summary: "{one-line goal}"
  detail: "{2-3 sentences expanding the goal}"
  non_goals:
    - "{what this is NOT}"

constraints:
  must:
    - "{absolute requirement}"
  must_not:
    - "{absolute prohibition}"
  should:
    - "{preferred but negotiable}"

acceptance_criteria:
  - id: "AC-001"
    description: "{testable criterion}"
    verification: "manual | automated | both"
    priority: "must | should | nice"
    complexity: "low | medium | high"
    # low: 단순 CRUD, 설정, UI → Direct 구현
    # medium: 비즈니스 로직, 데이터 변환 → Pair Mode 선택적
    # high: 결제/보안/외부연동/복잡한 상태 → Pair Mode 강제
  - id: "AC-002"
    description: "..."

ontology:
  entities:
    - name: "{EntityName}"
      fields:
        - name: "{fieldName}"
          type: "{string | number | boolean | date | reference}"
          required: true
      relationships:
        - target: "{OtherEntity}"
          type: "{has_many | belongs_to | has_one}"
  actions:
    - name: "{actionName}"
      actor: "{who performs this}"
      input: "{what goes in}"
      output: "{what comes out}"
      side_effects:
        - "{what changes}"

scope:
  mvp:
    - "{what's in MVP}"
  future:
    - "{what's deferred}"

tech_decisions:
  - decision: "{what was decided}"
    reason: "{why}"
    alternatives_considered:
      - "{what else was considered}"
```

### Validation Checklist

Before saving, verify:
- [ ] Goal summary is one clear sentence
- [ ] At least 1 must constraint
- [ ] At least 1 must_not constraint
- [ ] At least 2 acceptance criteria
- [ ] All AC are testable (not vague)
- [ ] All AC have complexity field (low/medium/high)
- [ ] Ontology has at least 1 entity
- [ ] MVP scope is defined
- [ ] No TODO/TBD placeholders

### Complexity 판단 기준

AC의 complexity를 다음 기준으로 판단:

| Complexity | 기준 | 예시 |
|-----------|------|------|
| **low** | 단일 레이어, 명확한 입출력, 표준 패턴 | CRUD 엔드포인트, 정적 페이지, 설정 파일 |
| **medium** | 2+ 레이어 관련, 비즈니스 규칙 포함, 데이터 변환 | 필터링/정렬 로직, API 통합, 데이터 집계 |
| **high** | 3 레이어 전체, 외부 연동, 보안, 복잡한 상태 관리 | 결제/정산, 인증/권한, 실시간 통신, 트랜잭션 |

### Output

```
Seed v{N} generated: .harness/ouroboros/seeds/seed-v{N}.yaml

Ontology: {N} entities, {M} actions
Acceptance Criteria: {K} items ({must} must, {should} should)
MVP Scope: {items}

Next: /run to execute Double Diamond
```
