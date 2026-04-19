# Changelog

## v2.1.0 — 2026-04-19

### Pair Mode — Navigator-Driver Pattern (실험적 → 실행 가능)

Pair Mode가 "설계 문서"에서 "실제 작동하는 오케스트레이션"으로 전환되었습니다.

#### 변경 사항

- **AC complexity 기반 자동 모드 전환**: 환경변수 토글(`HARNESS_ENABLE_PAIR_MODE=1`) 대신,
  seed spec의 각 AC에 `complexity: low | medium | high` 필드를 추가하여 AC 단위로 Pair Mode를
  선택적으로 활성화합니다.

- **Mixed Mode 지원**: 하나의 seed spec 내에서 low(direct) + medium/high(pair)를 혼합하여
  실행합니다. low AC를 먼저 구현하여 기반을 마련한 뒤, medium/high AC에 Pair Mode를 적용합니다.

- **Navigator — persistent background agent**: 기존 단방향 Agent 호출 대신
  `run_in_background: true`로 spawn하고 `SendMessage`로 양방향 통신합니다.
  세션 동안 실패 히스토리, 시도 횟수, 완료된 AC 목록을 유지합니다.

- **Test Designer — worktree 격리**: `isolation: "worktree"`로 실행하여 구현 코드(src/)에
  물리적으로 접근할 수 없게 합니다. seed spec과 AC만으로 테스트를 설계하여 구현 편향을 제거합니다.

- **자동 /review 체크포인트**: Pair Mode AC 3개 완료마다 인라인 드리프트 점검을 실행합니다.

- **`/run` 커맨드 재작성**: Phase 4를 Direct Deliver(4a)와 Pair Mode Deliver(4b)로 분리하고,
  구체적인 Agent/SendMessage 호출 코드를 포함하여 에이전트가 실제로 실행할 수 있게 합니다.

#### Seed Spec 변경

`acceptance_criteria`에 `complexity` 필드 추가 (선택적, 하위 호환):

```yaml
acceptance_criteria:
  - id: "AC-001"
    description: "..."
    complexity: "low"      # Pair Mode 스킵
  - id: "AC-002"
    description: "..."
    complexity: "high"     # Pair Mode + Test Designer 강제
```

`complexity` 필드가 없으면 기존 v2.0.0 방식(Direct Deliver)으로 동작합니다.

#### 에이전트 변경

- `navigator.md`: Lifecycle 섹션 추가 (background agent 통신 프로토콜), State Management 섹션 추가,
  검토 결과 포맷 표준화 (Pass/Retry/Switch/Escalate)
- `test-designer.md`: worktree 격리 실행 규칙 추가, 입력 방식 변경 (파일 경로 → 프롬프트 내 직접 포함)
- `topology.yaml`: `run-pair` 워크플로우 전면 재작성 (activation, mixed_mode, lifecycle 명시)

#### 기존 환경변수 (`HARNESS_ENABLE_PAIR_MODE=1`)

하위 호환을 위해 여전히 인식하지만, **권장하지 않습니다**. 이 환경변수가 설정되면 complexity 필드와
관계없이 모든 AC에 Pair Mode를 적용합니다. 새 프로젝트에서는 AC complexity 필드를 사용하세요.

#### Dogfooding 리포트

이 버전은 Marketing Dashboard 프로젝트의 dogfooding 결과를 기반으로 개선되었습니다.
이 버전은 Marketing Dashboard 프로젝트의 dogfooding 결과를 기반으로 개선되었습니다.

---

## v2.0.0 — 2026-04-12

### Breaking changes

- **Unified dotfolder layout**: `.ouroboros/` is now located under `.harness/ouroboros/`.
  Target projects that installed v1.x must run the migration script:

  ```bash
  <harness-repo>/scripts/migrate-v2.sh /path/to/your-project
  ```

  The script uses `git mv` when the old directory is tracked (preserving history) and
  falls back to `mv` otherwise. It also rewrites known v1 entries in `.gitignore`.

- **Path references in slash commands, agents, and Pro Python modules** now point to
  `.harness/ouroboros/...`. Re-running `init.sh` re-copies the updated commands/agents
  into `.claude/`.

### Why

The v1 layout created two sibling dotfolders (`.harness/` for tooling, `.ouroboros/` for
spec artifacts), which added noise in project roots and confused new users. Consolidating
under `.harness/` keeps the harness footprint in a single tree while preserving the
internal separation (`gates/`, `hooks/`, `ouroboros/`).

### Also in this release

- Installer no longer pre-creates empty `.ouroboros/{seeds,interviews,evaluations}`
  directories. Slash commands create them lazily on first use.
- Opt-in gate scripts (`check-complexity`, `check-mutation`, `check-performance`,
  `check-ai-antipatterns`) are no longer copied by default — see
  `.harness/gates/GATES.md` for how to enable them.

## v1.0.0 — Initial release

See git history.
