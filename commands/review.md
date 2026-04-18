---
description: Lightweight mid-run verification. Runs Stage 1 (Mechanical) gates only. Use between AC implementations to catch drift early. Much faster than /evaluate.
argument-hint: "[optional: specific gate to run, e.g. 'layers' or 'spec']"
---

# /review — 경량 중간 검증

> /evaluate의 Stage 1 (Mechanical)만 빠르게 실행한다.
> /run 중간에 드리프트를 조기 발견하는 용도.

## When to use
- /run 중 AC 3개 구현마다 (자동 또는 수동)
- 드리프트가 의심될 때
- /evaluate 전 빠른 사전 체크

## Instructions

### Step 1: Gate 실행 (Mechanical only)

다음 게이트만 실행한다 (/evaluate Stage 1과 동일):

```bash
# 레이어 위반 검사
bash .harness/gates/check-layers.sh

# 스펙 정합성 검사
bash .harness/gates/check-spec.sh

# 위반 탐지
bash .harness/gates/detect-violations.sh
```

특정 게이트만 실행 가능:
- `/review layers` → check-layers.sh만
- `/review spec` → check-spec.sh만
- `/review` (인자 없음) → 3개 전부

### Step 2: 간이 드리프트 측정

seed ontology의 핵심 엔티티가 코드에 존재하는지 확인:
1. `.harness/ouroboros/seeds/seed-v*.yaml`에서 ontology 엔티티 목록 추출
2. `src/` 디렉토리에서 해당 엔티티명 검색
3. 매칭률 계산:
   - 90%+ → OK
   - 70~90% → WARN (일부 엔티티 미구현 — 진행 단계에 따라 정상일 수 있음)
   - 70% 미만 → DRIFT (확인 필요)

### Step 3: 결과 요약

```
═══ /review ═══════════════════════════════════════

Gates:
  check-layers:      PASS | FAIL
  check-spec:        PASS | FAIL
  detect-violations: PASS | FAIL ({n} violations)

Drift (간이):
  Ontology match: {n}/{total} entities ({percentage}%)
  Status: OK | WARN | DRIFT

Verdict: PASS | WARN | FAIL
  → PASS: 계속 진행
  → WARN: 확인 후 계속 가능
  → FAIL: 즉시 수정 필요

Time: {elapsed}
═══════════════════════════════════════════════════
```

## /evaluate와의 차이

| | /review | /evaluate |
|---|---|---|
| Stage 1 (Mechanical) | O | O |
| Stage 2 (Semantic) | 간이 드리프트만 | 전체 AC 준수 검증 |
| Stage 3 (Judgment) | X | LLM 리뷰 |
| 소요 시간 | 1~3분 | 5~15분 |
| 용도 | 중간 점검 | 최종 검증 |
