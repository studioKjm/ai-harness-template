# Changelog

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
