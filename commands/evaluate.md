---
description: Run 3-stage verification (Mechanical gates → Semantic AC compliance → Judgment quality) after /run. ALWAYS run before committing. Blocks at Stage 1 failures — no Stage 2 until gates pass.
---

# /evaluate — 3-Stage Verification

> 구현 결과를 3단계로 검증한다

## Instructions

You are now the **Evaluator** agent. Verify the implementation against the seed spec.

### Phase 0: State Audit (FIRST STEP)

1. **Locate seed spec** — `.harness/ouroboros/seeds/seed-v*.yaml` (latest)
   - If none → abort: "No seed to evaluate against. Run /interview → /seed first."
2. **Check for prior evaluations** — `.harness/ouroboros/evaluations/`
   - If recent (<1h) PASS with no code changes → skip re-evaluation
   - If recent FAIL → surface prior findings; focus on whether they were addressed
3. **Detect scope** — which files changed since last commit? (`git diff --stat`)
   - Narrow evaluation to changed files when possible

### Subagent Delegation

검증의 정확도와 속도를 높이기 위해 **subagent를 활용**합니다:

```
Main Agent (Evaluator)
  ├─ Subagent → Stage 1 (Mechanical): 게이트 실행을 별도 에이전트에 위임
  │     └ .harness/detect-violations.sh 실행 + 결과 보고
  ├─ Main    → Stage 2 (Semantic): 시드 대비 AC/목표/제약 직접 검증
  └─ Main    → Stage 3 (Judgment): 코드 품질 판단
```

**Claude Code에서 subagent 사용**:
- Stage 1의 기계적 검증은 `Agent` 도구로 별도 subagent에 위임 가능
- subagent가 게이트 스크립트를 실행하고 결과만 반환
- 메인 에이전트는 Stage 2/3에 집중하여 병렬 처리 효과

### Stage 1: Mechanical Verification ($0 cost)

Run automated checks — these cost nothing and catch obvious issues:

```bash
# 1. Harness gates
.harness/detect-violations.sh

# 2. Layer separation check
.harness/gates/check-layers.sh

# 3. Lint (if available)
# TypeScript: npx eslint . --quiet
# Python: ruff check . || python -m flake8

# 4. Type check (if available)
# TypeScript: npx tsc --noEmit
# Python: mypy . || pyright

# 5. Build (if available)
# Next.js: npm run build
# Python: python -m py_compile

# 6. Tests (if available)
# npm test || pytest
```

**Report format**:
```
═══ Stage 1: Mechanical ═══════════════════════
  Harness Gates:    PASS | FAIL
  Layer Check:      PASS | FAIL | SKIP
  Lint:             PASS | FAIL | SKIP (not configured)
  Type Check:       PASS | FAIL | SKIP
  Build:            PASS | FAIL | SKIP
  Tests:            PASS | FAIL | SKIP
  ─────────────────────────────
  Result:           PASS | FAIL
```

If Stage 1 fails → stop. Fix mechanical issues before proceeding.

### Stage 2: Semantic Verification

Read the seed spec from `.harness/ouroboros/seeds/` and verify:

**2a. Acceptance Criteria Compliance**
For each AC in the seed:
```
  AC-001: "{description}"
    Status:   MET | PARTIALLY MET | NOT MET
    Evidence: "{file:line or explanation}"
    
  AC-002: "{description}"
    Status:   MET
    Evidence: "{file:line}"
```

**2b. Goal Alignment**
- Does the implementation solve the stated goal?
- Are there features NOT in the spec that were added? (scope creep)
- Are there non_goals that were accidentally implemented?

**2c. Constraint Compliance**
- Check each `must` constraint → is it satisfied?
- Check each `must_not` constraint → is it violated?

**2d. Ontology Drift**
- Do the actual data models match the seed's ontology?
- Are entity names, field names, relationships preserved?

**2e. Layer Architecture Compliance**
- 모든 Presentation 코드가 presentation 디렉토리에 있는가?
- 모든 Logic 코드가 logic/services 디렉토리에 있는가?
- 모든 Data 코드가 data/repositories 디렉토리에 있는가?
- Presentation → Data 직접 import가 없는가?
- Logic → Presentation 역의존이 없는가?
- 레이어 간 통신이 DTO/Interface를 통해서 이루어지는가?

```bash
# 자동 검사
.harness/gates/check-layers.sh
```

**2f. Test Coverage by Layer**
- Logic 레이어 테스트: 순수 비즈니스 로직이 테스트되고 있는가?
- 각 모듈의 책임만 정확히 테스트하고 있는가?
- mock이 레이어 경계에서만 사용되고 있는가?

**Report format**:
```
═══ Stage 2: Semantic ═════════════════════════
  AC Compliance:    {met}/{total} criteria met
  Goal Alignment:   ALIGNED | DRIFTED
  Constraint Check: PASS | VIOLATION ({detail})
  Ontology Drift:   LOW | MEDIUM | HIGH
  Layer Compliance: PASS | VIOLATION ({detail})
  Test by Layer:    Logic {%} | Data {%} | Presentation {%}
  ─────────────────────────────
  Result:           PASS | FAIL
```

### Stage 3: Judgment (optional)

Only run if Stage 2 has ambiguous results:

Review the overall quality:
- Is the code readable and maintainable?
- Are edge cases handled?
- Is error handling appropriate?
- Would this pass code review?

```
═══ Stage 3: Judgment ═════════════════════════
  Code Quality:     {1-5}/5
  Edge Cases:       COVERED | GAPS ({list})
  Error Handling:   ADEQUATE | INSUFFICIENT
  Review Ready:     YES | NO ({reason})
  ─────────────────────────────
  Result:           PASS | FAIL
```

### Final Verdict

```
═══ EVALUATION SUMMARY ════════════════════════
  Stage 1 (Mechanical): {PASS|FAIL}
  Stage 2 (Semantic):   {PASS|FAIL}
  Stage 3 (Judgment):   {PASS|FAIL|SKIP}
  ═════════════════════════════
  VERDICT:              PASS | FAIL

  {If FAIL}
  Issues to fix:
    1. {issue}
    2. {issue}
  
  Recommendation: Fix issues and re-run /evaluate

  {If PASS}
  Implementation verified against seed spec.
  Ready for commit/PR.
```

### Save Results

Save to `.harness/ouroboros/evaluations/eval-{seed-version}-{date}.yaml`:
```yaml
date: "YYYY-MM-DDTHH:MM:SS"
seed_ref: "seed-v{N}.yaml"
stages:
  mechanical:
    result: "pass|fail"
    details: {}
  semantic:
    result: "pass|fail"
    ac_compliance: {met: N, total: M}
    goal_alignment: "aligned|drifted"
    ontology_drift: "low|medium|high"
  judgment:
    result: "pass|fail|skip"
verdict: "pass|fail"
issues: []
```
