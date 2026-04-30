# /mikado — Mikado Method Manager

**Methodology**: mikado-method  
**Purpose**: Tree-based incremental refactoring. Try → fail → revert → discover prerequisites → solve leaves first.

---

## Usage

```
/mikado new <goal> [--hypothesis <text>]
/mikado try <graph-id> <node-id> [--notes <text>]
/mikado block <graph-id> <node-id> --prereq <desc> [<desc>...] [--desc <text>]
/mikado done <graph-id> <node-id>
/mikado revert <graph-id> <node-id>
/mikado tree <graph-id>
/mikado show <graph-id> <node-id>
/mikado list [--state in-progress|done|abandoned]
/mikado abandon <graph-id> [--reason <text>]
```

---

## The Mikado Algorithm

```
1. SET GOAL
   /mikado new "replace PostgreSQL driver"

2. TRY the change
   /mikado try mik-20260430-001 root

3a. IF it works (compiles, tests pass):
   /mikado done mik-20260430-001 root   ← graph complete 🎊

3b. IF it breaks (compile errors, test failures):
   → WRITE DOWN the prerequisites
   /mikado block mik-20260430-001 root --prereq "extract ConnectionPool interface" "add type alias for QueryResult"
   → REVERT all changes
   git checkout HEAD -- .
   /mikado revert mik-20260430-001 root

4. WORK ON LEAVES (nodes with no prerequisites)
   /mikado try mik-20260430-001 node-001
   ... (repeat from step 2 for each leaf node)

5. WHEN LEAVES DONE → retry parent
   /mikado try mik-20260430-001 root    ← prerequisites now done
```

**Key principle**: Always work on leaves. Never commit broken intermediate state.

---

## Node State Machine

```
⬜ pending  ──try──→  🟡 attempted  ──done──→  ✅ done
                           │
                        block (prereqs discovered)
                           ↓
                       🔴 blocked  ──try──→  🟡 attempted (when prereqs done)
                           │
                  ←──revert (back to pending)
```

---

## Example Session

```bash
# 1. Define goal
python3 methodologies/mikado-method/scripts/mikado.py new \
  "replace raw SQL with ORM"

# 2. Try the goal
python3 methodologies/mikado-method/scripts/mikado.py try mik-20260430-001 root

# 3. Hit compile errors — write prerequisites, revert
python3 methodologies/mikado-method/scripts/mikado.py block mik-20260430-001 root \
  --prereq "add ORM entity for User" "add ORM entity for Order" "configure ORM connection pool"
git checkout HEAD -- .
python3 methodologies/mikado-method/scripts/mikado.py revert mik-20260430-001 root

# 4. Visualize
python3 methodologies/mikado-method/scripts/mikado.py tree mik-20260430-001
# 🎯 Graph: mik-20260430-001  [in-progress]
# ⬜ root [pending] "replace raw SQL with ORM"
#    ├── ⬜ node-001 [pending] "add ORM entity for User"
#    ├── ⬜ node-002 [pending] "add ORM entity for Order"
#    └── ⬜ node-003 [pending] "configure ORM connection pool"

# 5. Work on leaves
python3 methodologies/mikado-method/scripts/mikado.py try mik-20260430-001 node-001
# ... write User entity, tests pass
python3 methodologies/mikado-method/scripts/mikado.py done mik-20260430-001 node-001

# 6. Retry root when all prerequisites done
python3 methodologies/mikado-method/scripts/mikado.py try mik-20260430-001 root
python3 methodologies/mikado-method/scripts/mikado.py done mik-20260430-001 root
```

---

## Agent Notes

When executing `/mikado`:

1. **Always revert before blocking** — the codebase must stay green after each session.
2. **Small nodes** — each prerequisite should be a small, independently committable change.
3. **Leaves first** — use `/mikado tree` to find nodes with `prerequisites: []` and work those.
4. **No half-done state committed** — `git checkout HEAD -- .` is a feature, not a failure.
5. **Combine with parallel-change** — large API changes often need parallel-change to be safe leafs.

---

## vs. Other Refactoring Methods

| Method | Scope | Use when |
|--------|-------|---------|
| `parallel-change` | Single function/API | Breaking API signature change |
| `strangler-fig` | Module/service level | Replacing a whole subsystem |
| `mikado-method` | Any size, tree | Complex refactoring with unknown dependencies |
