# /lean — Lean MVP Hypothesis Manager

**Methodology**: lean-mvp  
**Purpose**: Build→Measure→Learn cycle. One metric. Pivot or persist.

---

## Usage

```
/lean new --title <title> [--statement <text>] [--metric <name>] [--target <threshold>]
           [--window <days>] [--story <id>] [--tags <tag1,tag2>]
/lean build <hyp-id> [--mvp <description>] [--metric <name>] [--target <value>]
/lean measure <hyp-id> --actual <value> [--source <data-source>]
/lean decide <hyp-id> persist|pivot|abandon --rationale <text> [--decided-by <name>]
/lean status <hyp-id>
/lean list [--state proposed|testing|measuring|decided]
/lean link <hyp-id> [--story <id>] [--rfc <id>] [--tdd <id>] [--parent <id>]
```

---

## State Machine

```
      new
       ↓
  💡 proposed  ──build──→  🔨 testing  ──measure──→  📏 measuring
                                                           │
                                                         decide
                                                    ┌──────┴──────┐
                                               persist          pivot / abandon
                                                    │               │
                                                ✅ decided     💡 new hypothesis
```

**Key invariant**: `decided` requires `metric_actual` to be populated.  
A pivot creates a new hypothesis via `--next-hyp`.

---

## Workflow

### 1. Define the hypothesis

```bash
python3 methodologies/lean-mvp/scripts/lean.py new \
  --title "email-nudge-increases-retention" \
  --statement "We believe that a 3-day re-engagement email will increase 30-day retention by 5% for inactive users" \
  --metric "30d_retention_rate" \
  --target "> 40% (currently 35%)" \
  --window 14
```

### 2. Build the MVP

```bash
# After shipping minimal feature:
python3 methodologies/lean-mvp/scripts/lean.py build hyp-20260430-001 \
  --mvp "3-day inactive user email with personalized content"
```

### 3. Collect data

```bash
# After measurement window closes:
python3 methodologies/lean-mvp/scripts/lean.py measure hyp-20260430-001 \
  --actual "38.2%" \
  --source "Mixpanel 30d retention report"
```

### 4. Decide

```bash
# Not enough: pivot
python3 methodologies/lean-mvp/scripts/lean.py decide hyp-20260430-001 pivot \
  --rationale "38.2% missed 40% target; email open rate 12% suggests deliverability issue" \
  --decided-by "product-team"

# Create follow-up hypothesis
python3 methodologies/lean-mvp/scripts/lean.py new \
  --title "email-timing-pivot" \
  --statement "We believe that sending at user's local 9am instead of UTC noon will improve open rate to 25%+" \
  --metric "email_open_rate" --target "> 25%"
```

---

## Agent Notes

When executing `/lean`:

1. **One metric rule** — resist tracking multiple metrics. Pick the single number that proves/disproves the hypothesis.
2. **Time-box measurement** — always set `--window`. Without a deadline, measuring continues indefinitely.
3. **Pivot ≠ failure** — a pivot means the hypothesis taught us something and we're learning faster.
4. **Minimum viable** in MVP — the smallest change that lets you measure. Not a full feature.
5. **Link to TDD** — if the MVP needs implementation, create a `/tdd new` cycle and link: `/lean link <id> --tdd <tdd-id>`.

---

## Composition with Other Methodologies

| With | How |
|------|-----|
| `ouroboros` | Hypothesis → seed spec → implement → measure |
| `tdd-strict` | Each lean MVP implementation cycle: TDD-driven |
| `observability-first` | SLO as measurement metric for lean hypothesis |
| `rfc-driven` | Large experiments require RFC before building |
