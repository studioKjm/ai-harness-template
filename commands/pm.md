---
description: Generate a stakeholder-facing PRD from interview results. USE WHEN non-engineering stakeholders need a Product Requirements Document. Optional — most workflows go interview → seed directly.
---

# /pm — PRD Generator

> 인터뷰 결과를 PRD(Product Requirements Document)로 변환한다

## Instructions

Read the latest interview from `.ouroboros/interviews/` and generate a PRD.

### PRD Structure

```markdown
# PRD: {Project/Feature Name}

## Overview
- **Date**: YYYY-MM-DD
- **Author**: {from interview}
- **Status**: Draft
- **Source**: Interview {ref}

## Problem Statement
{What problem are we solving? Why does it matter?}

## Goals
### Must Have (P0)
- {goal from constraints.must}

### Should Have (P1)
- {goal from constraints.should}

### Nice to Have (P2)
- {from scope.future}

## Non-Goals
- {from goal.non_goals}

## User Stories
- As a {actor}, I want to {action} so that {benefit}

## Technical Requirements
### Architecture
{From ontology and tech_decisions}

### Data Model
{From ontology.entities — formatted as table}

| Entity | Fields | Relationships |
|--------|--------|---------------|
| {name} | {fields} | {relations} |

### API / Interface
{From ontology.actions}

### Constraints
- MUST: {constraints.must}
- MUST NOT: {constraints.must_not}

## Acceptance Criteria
{From seed AC, formatted as checklist}
- [ ] AC-001: {description}
- [ ] AC-002: {description}

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| {from interview assumptions_surfaced} | {H/M/L} | {mitigation} |

## Timeline
- MVP: {scope.mvp items}
- Future: {scope.future items}
```

### Output

Save to `docs/PRD-{name}-{date}.md` and display summary:

```
PRD generated: docs/PRD-{name}-{date}.md

Summary:
  P0 Goals: {count}
  P1 Goals: {count}
  User Stories: {count}
  Acceptance Criteria: {count}
  Risks: {count}
```
