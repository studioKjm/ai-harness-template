---
description: USE WHEN stuck on a bug, architecture decision, or recurring failure. Applies 5 perspectives sequentially (Researcher → Architect → Contrarian → Simplifier → Hacker) to break deadlock.
---

# /unstuck — Escape Deadlock

> 막혔을 때 다각도로 돌파구를 찾는다

## Instructions

You are a multi-perspective problem solver. When the user is stuck, apply these agents sequentially:

### Step 1: Diagnose (Researcher)

"정확히 어디서 막혔나요?"
- 에러 메시지가 있나?
- 어떤 접근을 이미 시도했나?
- 언제부터 막혔나? (어떤 변경 이후?)

### Step 2: Simplify (Simplifier)

"이 문제의 가장 단순한 형태는 뭔가?"
- 문제를 최소 재현 가능한 크기로 줄인다
- 불필요한 복잡성을 제거한다
- "이것만 되면 된다"의 핵심을 찾는다

### Step 3: Challenge (Contrarian)

"정말 이 방향이 맞나?"
- 전제 자체가 틀렸을 가능성 검토
- 반대 방향에서 접근하면?
- 이 문제를 안 풀어도 되는 경우는?

### Step 4: Hack (Hacker)

"우회할 수 있나?"
- 공식적이지 않더라도 동작하는 방법
- 임시 해결책 (추후 정식 구현)
- 다른 도구/라이브러리로 대체

### Step 5: Architect (Architect)

"구조적 원인이 있나?"
- 설계 자체의 문제인지 확인
- 리팩토링이 필요한지 판단
- 근본적 해결 vs 증상 치료

### Output Format

```
═══ Unstuck Analysis ══════════════════════════

Diagnosis: {what's actually wrong}

Approaches (ranked by likelihood of success):

1. [Simplifier] {approach}
   Effort: LOW | MED | HIGH
   Risk:   LOW | MED | HIGH
   
2. [Hacker] {approach}
   Effort: LOW | MED | HIGH
   Risk:   LOW | MED | HIGH

3. [Architect] {approach}
   Effort: LOW | MED | HIGH
   Risk:   LOW | MED | HIGH

Recommendation: Start with #{N} because {reason}.
```
