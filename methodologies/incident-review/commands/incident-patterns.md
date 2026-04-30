---
description: Analyze recurring root causes and contributing factors across incidents. Provided by the Incident Review methodology.
---

# /incident-patterns — Pattern Analysis Across Incidents

> One incident is bad luck. Three with the same root cause is a system flaw.

## When to use

- Quarterly retrospective — surface recurring causes
- Before deciding on a major architecture change — validate it addresses real pain
- After a sev1 — check if you've seen the same pattern before
- When deciding what to invest in (monitoring? testing? refactoring?)

## Usage

```
/incident-patterns [--days N]
```

Default: last 90 days. Adjust based on incident volume.

## Output format

```
Incident pattern analysis (last 90 days)
──────────────────────────────────────────────────
Total incidents: 12
By severity:
  sev1: 1
  sev2: 3
  sev3: 6
  sev4: 2

Top root causes (recurring):
  [3x] DB connection pool exhausted under load spike
  [2x] Stale cache served deleted data

Contributing factor categories:
   5x  monitoring
   4x  documentation
   3x  testing
   2x  deployment
```

## Instructions

### Step 1 — Run the script

```shell
python3 .harness/methodologies/incident-review/scripts/inc.py patterns --days 90
```

### Step 2 — Interpret recurrence

| Recurrence | Meaning | Action |
|-----------|---------|--------|
| 1x cause | Probably bad luck | Note, but don't over-engineer |
| 2x cause (different incidents) | Suspicious | Investigate why action items from first didn't prevent second |
| 3x+ cause | Systemic flaw | Major investment justified — refactor / new monitoring / process change |

### Step 3 — Interpret contributing factors

Categories aggregate across all incidents (not just recurring ones). Top categories indicate **investment areas**:

- `monitoring` >5x → invest in observability (consider `+ observability-first` methodology when added)
- `documentation` >5x → invest in runbooks
- `testing` >5x → invest in test coverage / CI
- `deployment` >5x → invest in rollout safety
- `dependencies` >5x → audit external services

### Step 4 — Convert pattern findings to durable artifacts

Recurring patterns should become:

| Pattern | Artifact |
|---------|---------|
| Same root cause 3x+ | New ADR documenting the systemic issue + decision |
| Single category dominating | New methodology adoption (e.g., observability-first) |
| Specific class of action items always slipping | Process change (e.g., "all action items must have <2 week due") |

### Step 5 — Reporting

```
> "Pattern analysis complete.
>  Top recurring root cause: '{cause}' ({N}x in {days} days).
>  Recommendation: {action_based_on_recurrence}.
>  Top contributing factor category: '{category}' ({N}x).
>  Recommendation: {investment_suggestion}."
```

## Filters

The script reads ALL `.harness/incident-review/incidents/*.yaml` files within the time window. To narrow:

```bash
# Only published+ (skip in-progress incidents)
python3 inc.py list --status published > /tmp/published-ids.txt
# Then manually read those files

# Only sev1/sev2 (most impactful)
python3 inc.py patterns --days 180 | grep -E "sev1|sev2"
```

(Future v0.2: add `--severity-min` filter to script.)

## Constraints

- Only counts incidents with non-empty `five_whys.root_cause`
- Recurrence detection uses string match (lowercase) — semantically similar but worded differently won't match. Encourage consistent vocabulary in root_cause.
- Does NOT include archived incidents by default (they're outside `--days` window typically)

## Anti-patterns

- ❌ Running analysis but ignoring patterns — surfacing without acting wastes the postmortem
- ❌ "We can't reproduce, must be flaky" repeated 5x — that IS the pattern
- ❌ Aggregating root causes manually in a spreadsheet — defeats the purpose of structured records

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| "no recurring root causes" but you remember the same issue | Inconsistent root_cause wording | Standardize vocabulary; consider tagging |
| Many incidents shown but no patterns | Each incident genuinely unique (early stage product) | Wait for more data, lower bar |
| Same incident appears multiple times | Bug in your YAML — check for duplicate IDs | `find .harness/incident-review/incidents/ -name "*.yaml" \| sort \| uniq -d` |
