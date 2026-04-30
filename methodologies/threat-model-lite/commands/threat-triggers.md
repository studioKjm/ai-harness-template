---
description: View or update trigger keywords/paths that auto-require threat models. Provided by the Threat Model (Lite) methodology.
---

# /threat-triggers — Configure What Auto-Requires Threat Models

> Tune the list of "sensitive" patterns that warn when uncovered.

## When to use

- First time using threat-model-lite — review default triggers
- Project has unusual sensitive entities not in defaults (e.g., `health_record`, `tax_id`)
- Some default triggers don't apply (e.g., no payment in this project)
- Want to add custom file path patterns

## Usage

```
/threat-triggers show              # Print current triggers
/threat-triggers add-pattern --category CAT --pattern "..."
/threat-triggers add-path "PATH-GLOB"
/threat-triggers exempt --path "..." --reason "..."
/threat-triggers init              # Re-initialize from default template
```

## Default triggers

The bundled `triggers.yaml` covers:

| Category | Patterns | Severity |
|----------|---------|---------|
| authentication | auth*, login*, password, session, token, jwt, oauth, saml, sso, mfa, 2fa | high |
| payment | payment, billing, invoice, refund, charge, subscription, checkout, card, wallet | critical |
| pii | email, phone, ssn, name, address, kyc, identity, passport, birthdate | high |
| authorization | admin, role, permission, rbac, abac, scope, grant | high |
| secrets | secret, api_key, apikey, private_key, credential | critical |

Plus path patterns:
- `**/auth/**`, `**/payment/**`, `**/billing/**`, `**/admin/**`, `**/security/**`

Plus endpoint patterns:
- `POST /login`, `POST /signup`, `POST /password/*`, `*/admin/*`, `POST /payment/*`, `POST /webhook/*`

## Instructions

### Step 1 — Read current triggers

```shell
cat .harness/threat-model-lite/triggers.yaml
```

If the file doesn't exist (methodology just activated), copy from template:
```shell
cp .harness/methodologies/threat-model-lite/templates/triggers.yaml \
   .harness/threat-model-lite/triggers.yaml
```

### Step 2 — Edit triggers.yaml directly

The triggers file is a hand-edit YAML. Add/remove categories, patterns, paths, endpoints. Schema:

```yaml
sensitive_entities:
  <category-name>:
    patterns: ["pattern1", "pattern2*"]
    severity: low | medium | high | critical

sensitive_paths:
  - "**/glob/pattern/**"

sensitive_endpoints:
  - "POST /route"
  - "GET /route/*"

exemptions:
  paths: ["specific/path/that/is/safe"]
  reasons:
    "specific/path/that/is/safe": "documented reason"
```

### Step 3 — Validate

```shell
python3 -c "import yaml; print(yaml.safe_load(open('.harness/threat-model-lite/triggers.yaml')))"
```

If yaml parses: gate will pick up changes on next run.

### Step 4 — Test against codebase

```shell
python3 .harness/methodologies/threat-model-lite/scripts/tm.py scan
```

Lists files matching sensitive paths but no threat model linked.

## Pattern syntax

| Type | Syntax | Example | Matches |
|------|--------|---------|---------|
| Entity keyword | substring (case-insensitive) | `password` | "User.password", "PASSWORD_RESET" |
| Entity wildcard | trailing `*` | `auth*` | "auth", "auth_handler", "authenticate" |
| Path glob | `**` for any depth, `*` for single segment | `**/auth/**` | any path containing /auth/ |
| Endpoint | HTTP method + path | `POST /webhook/*` | POST /webhook/stripe |

## Exemption rules

Exempt with care — every exemption is a maintenance hazard.

```yaml
exemptions:
  paths:
    - "src/admin/__tests__/"
  reasons:
    "src/admin/__tests__/": "test fixtures, no production code"
```

Reason field is mandatory in spirit (gate doesn't enforce, but reviewers should reject exemptions without reasons).

## Constraints

- Triggers file is project-local — different projects can have different triggers
- Default file is bundled in template; copying is idempotent
- Pattern matching is intentionally simple — heuristic, not exhaustive
- False positives are expected (user verifies); false negatives are dangerous (user adds patterns when discovered)

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| Gate warns on test files | Test code legitimately touches auth | Add path to `exemptions.paths` with reason |
| Real sensitive code not warned | Pattern not in triggers | Add new pattern under appropriate category |
| `triggers.yaml not found` on scan | Methodology activated but file not initialized | Copy from template (see Step 1) |
| Glob doesn't match expected files | Glob syntax mistake | Test with `find` or `python3 -c "from pathlib import Path; print(list(Path('.').rglob('PATTERN')))"` |
