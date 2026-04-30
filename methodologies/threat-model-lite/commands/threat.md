---
description: Manage STRIDE threat models — security analysis at design time. Provided by the Threat Model (Lite) methodology.
---

# /threat — STRIDE Threat Modeling

> Assume the attacker has read your spec. Threat-model BEFORE you code, not after.

## When to use

- Story/feature touches sensitive entity (auth, payment, PII, admin)
- New endpoint added (especially webhooks, public APIs)
- Architecture change affects trust boundaries
- Compliance requirement (PCI-DSS, GDPR, internal security policy)

## Usage

```
/threat new <slug> --target-kind story|spike|feature|endpoint|module --target-ref REF
/threat list [--status draft|reviewed|approved|applied]
/threat show <model-id>
/threat add <model-id> --category S|T|R|I|D|E --threat "..." --mitigation "..." [...]
/threat review <model-id>          # draft → reviewed (validates STRIDE coverage)
/threat approve <model-id>         # reviewed → approved
/threat apply <model-id>           # approved → applied
/threat link <model-id> --to story-id|spike-id|adr-id
/threat scan [--path GLOB]         # find sensitive paths without threat model
```

## STRIDE — what each letter means

| Letter | Category | Example threats |
|--------|----------|----------------|
| **S** | Spoofing | Impersonation, credential stuffing, session hijack |
| **T** | Tampering | Data modification in transit/storage, parameter tampering |
| **R** | Repudiation | User denies action, missing audit log, untrusted timestamps |
| **I** | Information Disclosure | Data leak, verbose errors, side-channel, IDOR |
| **D** | Denial of Service | Flood, resource exhaustion, algorithmic complexity |
| **E** | Elevation of Privilege | Privilege escalation, IDOR with admin actions, path traversal |

## State machine

```
[draft] → [reviewed] → [approved] → [applied]
            ↓             ↓
         [draft]      [reviewed]    (rollback allowed)
```

| State | Meaning | Move when |
|-------|---------|-----------|
| draft | Analysis in progress | All STRIDE categories addressed |
| reviewed | STRIDE coverage validated | Stakeholder approval |
| approved | Ready to implement | Mitigations shipped |
| applied | Mitigations live | (terminal) |

## Instructions

### Step 1 — Locate the script

```
.harness/methodologies/threat-model-lite/scripts/tm.py
```

### Step 2 — Run the requested subcommand

```shell
# Create model linked to a story
python3 .harness/methodologies/threat-model-lite/scripts/tm.py \
  new password-reset \
  --target-kind story \
  --target-ref st-2026-04-30-password-reset \
  --description "Password reset flow with email link"

# Add threats per STRIDE category
python3 .harness/methodologies/threat-model-lite/scripts/tm.py \
  add tm-2026-04-30-password-reset \
  --category S \
  --threat "Attacker uses leaked email to request reset for victim" \
  --mitigation "Rate limit reset requests per email (5/hour)" \
  --mitigation "SMS notification to account owner on reset" \
  --likelihood medium \
  --impact high
```

### Step 3 — Edit yaml for fields the script doesn't cover

Manually edit `.harness/threat-model-lite/models/<id>.yaml` to fill:
- `assets[]` — what's at risk
- `trust_boundaries[]` — where data crosses zones
- `compliance.frameworks` — relevant standards
- For categories that genuinely don't apply: set `stride.<category>.not_applicable_reason: "..."`

### Step 4 — Review (gate-checked)

```shell
python3 .harness/methodologies/threat-model-lite/scripts/tm.py \
  review tm-2026-04-30-password-reset
```

Script blocks if any STRIDE category has 0 threats AND no `not_applicable_reason`.
Override with explicit reason: `--override "We accept residual S risk for v1, see ADR-X"`.

### Step 5 — Reporting

After `new`:
> "Threat model `{id}` created (target: {kind}/{ref}).
>  Add threats per STRIDE: `/threat add {id} --category S|T|R|I|D|E ...`.
>  When all 6 categories addressed: `/threat review {id}`."

After `review`:
> "Threat model `{id}`: draft → reviewed. {N} threats across {M} categories.
>  Approve when stakeholders sign off: `/threat approve {id}`."

After `apply`:
> "Threat model `{id}`: approved → applied. All mitigations implemented.
>  Future related work should reference this model via `/threat link`."

## Composition with other methodologies

| Combo | Effect |
|-------|--------|
| `+ bmad-lite` | pm-strict suggests `/threat new` when story narrative matches trigger keywords |
| `+ ouroboros` | Threat model becomes evidence for seed AC ("system MUST rate limit...") |
| `+ exploration` | Spike measures specific attack feasibility, learning feeds threat model |
| `+ incident-review` | Past incidents inform threat models (links.related_incidents) |
| `+ parallel-change` | Migration plans must check that mitigations are preserved during cutover |

## Constraints

- One STRIDE category cannot be skipped silently — must have ≥1 threat OR `not_applicable_reason`
- `--mitigation` can be repeated for multiple controls
- `mitigation_status: deferred` for high/critical assets requires `residual_risks[]` entry
- `applied` state requires all mitigations be `implemented`/`deferred`/`accepted` (no `planned` left)
- `apply --force` records audit trail in history but does NOT bypass coverage check

## Anti-patterns

- ❌ Single mitigation for multiple threats — write each threat separately
- ❌ Mitigation: "use HTTPS" with no other detail (cert pinning? HSTS? rotation?)
- ❌ Skipping repudiation as "not applicable" — almost always has audit log component
- ❌ Threat model without linked story/spike/ADR — orphan model has no operational meaning
- ❌ Setting all likelihood=low to avoid mitigation — likelihood is observed, not chosen

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `STRIDE coverage incomplete` | Empty category | Add threat OR set `not_applicable_reason` |
| `unrecognized target prefix` on link | Custom ID format | Use st-/sp-/ADR-/inc-/tm- prefixes |
| Many `planned` mitigations on apply | Premature apply | Implement first, then advance |
| Same mitigation repeats across threats | Vague mitigation | Make each one specific to its threat |
