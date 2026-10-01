# Changelog

## v2.7.0 — 2026-10-01

Claude Code(2026-10 기준 공식 문서)에 맞춘 현행화와 Supabase 스택 지원.

### 수정 (기존 설치가 의도대로 동작하지 않던 부분)
- **권한 프리셋 문법**: `Bash(cmd:*)`는 현재 지원되지 않고 `Bash(cmd *)`만 유효하다. 3개 프리셋(strict/standard/permissive)을 새 문법으로 교체했고, `git push`는 `ask`로 분리했다. 기존 설치는 `init.sh`를 다시 실행하거나 프리셋을 수동 교체해야 한다.
- **훅 입력**: `post-edit-lint.sh`는 이제 stdin JSON(`tool_input.file_path`)을 읽는다. `$CLAUDE_FILE_PATH`는 공식 문서에 없어 제거했다. 인자로 경로를 주는 수동 호출은 그대로 동작한다. 훅 command는 `${CLAUDE_PROJECT_DIR}` 기준 경로를 쓴다.
- `PreCommit`은 Claude Code 이벤트가 아니라 git hook이다. `pre-commit-gate.sh`의 설명을 바로잡았다.

### 추가
- **`--settings-file shared|local`** (기본 `shared`): 권한·훅을 팀과 공유되는 `.claude/settings.json`에 설치한다. 이전 동작(`settings.local.json`)은 `--settings-file local`. `.claude/settings.local.json`은 `.gitignore`에 추가된다.
- **`--commands-as commands|skills`** (기본 `commands`): `skills`는 워크플로 커맨드를 `.claude/skills/<name>/SKILL.md`로 설치한다(`disable-model-invocation: true`, 직접 `/name`으로 호출). `.claude/commands/`도 계속 동작하며 기본값은 v3에서 `skills`로 바꿀 예정이다. 런타임 `/methodology use`가 복사하는 번들 커맨드는 아직 `.claude/commands/`를 쓴다.
- **Supabase 스택** (`supabase/config.toml` 또는 `@supabase/*` 의존성이 있으면 자동 감지, `stacks/supabase/`):
  - `gates/check-migrations.sh` (기본 게이트): 기존 마이그레이션 수정·삭제·이름변경 금지, 파일명 형식, 새 테이블의 RLS, `using (true)` 금지. 커밋 시엔 스테이징 기준, CI에선 `HARNESS_BASE_REF`(기본 `origin/main`)와 비교한다. 정당한 재작성은 `HARNESS_ALLOW_MIGRATION_REWRITE=1`. supabase 디렉터리가 없으면 아무것도 하지 않는다.
  - `pretool-guard.sh` (PreToolUse 훅): 원격 프로젝트 쓰기(`db push` 등), 기존 마이그레이션 편집, 운영 env 파일 접근, `--no-verify`를 결정적으로 차단한다.
  - skills `supabase-migration`, `verify`, 서브에이전트 `rls-security-reviewer`(읽기 전용), `.mcp.json`(next-devtools + **로컬** Supabase MCP), 권한 오버레이 자동 병합.
- `gates/lint-changed.py`: 변경한 줄의 lint 오류만 검사한다. 기존 오류가 많은 코드베이스에서 "손대는 코드만 깨끗하게"를 강제할 때 쓴다.

### 알려진 한계
- deny 규칙과 PreToolUse 훅은 정규식 기반이라 다단 셸 우회를 완전히 막지 못한다 (공식 문서도 같은 한계를 명시). `/sandbox` 병행 권장.
- `post-edit-lint.sh`는 여전히 `eslint --fix`/`prettier --write`로 파일을 자동 수정한다. 기존 코드가 포맷되지 않은 프로젝트에서는 범위 밖 diff가 생길 수 있어 주의.


## v2.6.0 — 2026-05-15

### Isolated AI Security Gate (`check-security-ai.sh`)

#### Problem

When the same AI agent that writes code also reviews its own security, confirmation bias dramatically reduces vulnerability detection rates. The agent subconsciously protects its own assumptions, missing the vulns it just introduced.

#### Solution

A new opt-in gate that spawns a **completely separate Claude process** with zero context from the coding session. The security agent receives only raw source code — no design docs, no specs, no intent comments. It finds vulnerabilities without knowing WHY the code was written.

#### Key behaviors

- **Context stripping**: Comments containing `Why:`, `Intent:`, `Design:`, `Spec:` are removed before the code is sent — the agent sees only behavior, not justification.
- **Adversarial persona**: The `security-agent-isolated.md` persona instructs the agent to treat every input as attacker-controlled and never give developers the benefit of the doubt.
- **Finding tracker**: Results accumulate in `.harness/security/findings.json`. Dismissed false positives go to `dismissed.txt` with a mandatory reason.
- **Exit policy**: `critical` or `high` severity → exit 1 (commit blocked). `medium` or `low` → exit 0 (warning only).
- **Auth**: Primary — `claude -p` CLI (Pro/Max subscription, no API key needed). Fallback — `ANTHROPIC_API_KEY` via urllib.

#### Files added

- `gates/check-security-ai.sh` — opt-in gate script
- `methodologies/threat-model-lite/personas/security-agent-isolated.md` — adversarial researcher persona
- `security/findings.json` — finding tracker template
- `security/dismissed.txt` — dismissal list template
- `security/dismiss-finding.sh` — dismissal helper

#### Enable

```bash
export HARNESS_ENABLE_AI_SECURITY=1
git commit  # gate runs automatically
```

Or run manually:

```bash
bash .harness/gates/check-security-ai.sh . --full-scan
```

#### Self-validation

During dogfooding on the marketingagent project, the security agent (analyzing the gate's own code) found two legitimate vulnerabilities:
- Passing `full_prompt` (80KB code bundle) as a CLI argv argument — fixed by switching to stdin
- Passing `ANTHROPIC_API_KEY` via `sys.argv` where it appears in process listing — fixed by reading from `os.environ`

This confirms the isolation design works: the agent was genuinely adversarial even against its own containing script.

#### NON-BREAKING

Existing installations are unaffected. Enable via `HARNESS_ENABLE_AI_SECURITY=1`.

---

## v2.5.3 — 2026-05-06

### Fix: /trd → /decompose → /run 워크플로우 강제 게이트

실사용 테스트에서 AI가 `/seed` 완료 후 `/trd`, `/decompose`를 생략하고 `/run`으로 바로 진행하는 문제를 수정합니다.

#### 원인

3곳의 구조적 공백이 동시에 작용:
1. `CLAUDE.md` 워크플로우 다이어그램에 `/trd`, `/decompose`가 누락
2. `/seed` 완료 메시지가 `Next: /run`으로 직접 유도
3. `/run` Prerequisites가 decompose 결과물 존재 여부를 체크하지 않음

#### 변경 사항

- **`templates/CLAUDE.md.hbs`**: Ouroboros 워크플로우 다이어그램을
  `interview → seed → run` 에서 `interview → seed → trd → decompose → run`으로 수정.
  skip 허용 조건 명시 (전체 AC가 `low` complexity이고 단일 레이어 변경인 경우만).

- **`commands/seed.md`**: Output 완료 메시지의 `Next: /run to execute Double Diamond`를
  3단계 순서 안내(`/trd → /decompose → /run`)로 교체. AC complexity별 카운트 표시 추가.

- **`commands/run.md`**: Prerequisites에 항목 4, 5 추가:
  - `docs/TRD.md` 미존재 시 **STOP** (skip 조건 외)
  - `.harness/ouroboros/tasks/` 미존재 시 **STOP** (skip 조건 외)

#### 영향 범위

NON-BREAKING. 기존 프로젝트에서 `/run` 전에 이미 TRD와 decompose를 실행하고 있다면 동작 변화 없음.
신규 설치에서는 `templates/CLAUDE.md.hbs`가 자동 반영됨. 기존 설치는 `commands/` 3개 파일 수동 복사.

---

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
