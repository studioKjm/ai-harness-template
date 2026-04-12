---
description: Evolve the system when /evaluate fails. Runs Wonder → Reflect → Re-seed cycle with fan-out multi-perspective analysis (Contrarian + Simplifier + Researcher). Stops at convergence (ontology similarity ≥ 0.95).
---

# /evolve — Evolution Loop

> 평가 결과를 반영하여 다음 세대로 진화한다

## Instructions

You are the **Evolver**. Your job is to analyze evaluation failures and evolve the system.

### Prerequisites
- Evaluation results must exist in `.ouroboros/evaluations/`
- If no evaluation, prompt to run `/evaluate` first

### Subagent Delegation (Fan-out)

진화 단계에서는 **다관점 분석을 위해 subagent를 병렬로 활용**합니다:

```
Main Agent (Evolver)
  ├─ Subagent(Contrarian)  → "이 실패가 정말 문제인가? 반대 관점은?"  (병렬)
  ├─ Subagent(Simplifier)  → "불필요한 복잡성이 원인은 아닌가?"     (병렬)
  ├─ Subagent(Researcher)  → "유사 사례/증거가 있는가?"            (병렬)
  └─ Main                  → 3개 관점 종합 → 규칙 진화 / Re-seed 결정
```

**Claude Code에서**: `Agent` 도구로 3개 subagent를 **한 번에 병렬 spawn**하여 시간 절약

### Evolution Cycle

```
┌─────────────────────────────────────────────┐
│                                             │
│  Evaluate → Wonder → Reflect → Re-seed     │
│     ↑                            │          │
│     └────────────────────────────┘          │
│                                             │
│  Stop when: ontology similarity >= 0.95     │
│         or: max 5 generations               │
└─────────────────────────────────────────────┘
```

### Phase 1: Wonder ("우리가 아직 모르는 것은?")

Read the latest evaluation and ask:
1. 실패한 AC가 있나? → 왜 실패했나?
2. 드리프트가 발생했나? → 스펙이 잘못됐나, 구현이 잘못됐나?
3. 예상 못 한 발견이 있었나?
4. 스펙에 빠진 것이 있었나?

### Phase 2: Reflect ("피드백을 다음에 반영")

1. **Gate Evolution** (Harness 연동):
   - 새로운 규칙 위반이 발견됐으면 → `.harness/gates/rules/` 에 규칙 추가
   - 기존 규칙이 너무 strict했으면 → 규칙 완화
   - 새로운 패턴이 발견됐으면 → `boundaries.yaml`에 추가

2. **Spec Evolution**:
   - 빠진 AC 추가
   - 잘못된 ontology 수정
   - constraint 조정

3. **Convention Evolution**:
   - 반복된 실수 → `docs/code-convention.yaml`에 규칙 추가
   - 새로운 패턴 → 컨벤션으로 등록

### Phase 3: Re-seed (선택적)

If the spec needs significant changes:
- Create `seed-v{N+1}.yaml` with learnings incorporated
- Reference previous version
- Document what changed and why

### Convergence Check

Compare current ontology with previous generation:

```
Ontology Similarity Calculation:
  Name overlap:  {count matching entity/field names} / {total} × 0.5
  Type match:    {count matching types} / {total} × 0.3
  Exact match:   {count identical definitions} / {total} × 0.2
  ─────────────────────────────
  Similarity:    {score} / 1.0
  
  {>= 0.95} → CONVERGED. Stop evolving.
  {< 0.95}  → Continue to next generation.
```

### Output

```
═══ Evolution Report ══════════════════════════
  Generation:        {N} → {N+1}
  Ontology Sim:      {score}
  Status:            CONVERGED | EVOLVING
  
  Changes:
    Gates added:     {count}
    AC modified:     {count}
    Ontology changes:{count}
    Conventions:     {count}
  
  {If EVOLVING}
  Next: /run to execute with evolved spec
  
  {If CONVERGED}
  System has stabilized. No further evolution needed.
```

### Anti-patterns (자동 감지)

Watch for these pathological patterns:
1. **Oscillation**: Same change being added and removed across generations
2. **Stagnation**: Similarity stuck at same value for 2+ generations  
3. **Explosion**: Ontology growing without convergence

If detected:
```
WARNING: {pattern} detected.
  Recommendation: Step back and re-interview.
  Run /interview to restart from fresh perspective.
```
