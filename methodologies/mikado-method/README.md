# Mikado Method — Methodology Plugin

> Goal → try → revert → 전제조건 발견 → 나뭇잎부터 해결 — 트리 기반 점진적 리팩터링.

## 목적

복잡한 리팩터링에서 **알 수 없는 의존성**을 안전하게 발굴. 각 시도는 항상 main으로 되돌릴 수 있는 상태를 유지하고, 발견된 전제조건을 트리로 시각화.

```
[리팩터링 목표 설정]
     ↓
/mikado new "replace DB driver"      — 루트 노드 생성
     ↓
/mikado try <graph> root             — 변경 시도
     ↓
  ┌─────────────┐
  │ 성공?        │
  │             │
  Yes           No
  ↓             ↓
done     전제조건 기록 → /mikado block <graph> root --prereq <desc>
                         git checkout HEAD -- .  (변경 되돌리기)
                         /mikado revert <graph> root
                              ↓
                         나뭇잎 노드 먼저 해결 → /mikado try <graph> <leaf>
                              ↓
                         전제조건 완료 후 재시도 → /mikado try <graph> root
```

## 활성화

```bash
/methodology use mikado-method
```

requires: 없음. parallel-change/strangler-fig 과 함께 "리팩터링 3종 세트"로 조합.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/mikado new <goal>` | 새 Mikado 그래프 생성 |
| `/mikado try <graph> <node>` | 노드 변경 시도 (pending/blocked → attempted) |
| `/mikado block <graph> <node>` | 전제조건 발견, 노드 차단 (attempted → blocked) |
| `/mikado done <graph> <node>` | 노드 완료 (attempted → done) |
| `/mikado revert <graph> <node>` | 변경 되돌리기 (back to pending) |
| `/mikado tree <graph>` | 트리 시각화 출력 |
| `/mikado show <graph> <node>` | 노드 상세 확인 |
| `/mikado list` | 전체 그래프 목록 |

## 노드 상태 기계

```
⬜ pending  ──try──→  🟡 attempted  ──done──→  ✅ done
                           │
                     block (전제조건 발견)
                           ↓
                       🔴 blocked  ──try──→  🟡 attempted (전제조건 완료 후)
```

**불변 조건**: 노드가 done이 되려면 모든 prerequisites가 done이어야 함.

## 산출물

```
.harness/mikado-method/
├── graphs/mik-YYYYMMDD-NNN.yaml   # 그래프별 트리 상태
└── ...
.harness/state/mikado-method.yaml
```

## 트리 시각화 예시

```
🎯 Graph: mik-20260430-001  [in-progress]
   Goal: replace raw SQL with ORM

⬜ root [pending] "replace raw SQL with ORM"
├── ✅ node-001 [done] "add ORM entity for User"
├── 🟡 node-002 [attempted] "add ORM entity for Order"
└── ⬜ node-003 [pending] "configure ORM connection pool"

Progress: ✅ 1 done  🔴 0 blocked  ⬜ 2 pending / 4 total
```

## 리팩터링 3종 세트

| 방법론 | 범위 | 사용 시점 |
|-------|------|---------|
| `parallel-change` | 함수/API | Breaking change 시그니처 변경 |
| `strangler-fig` | 모듈/서비스 | 서브시스템 전체 교체 |
| `mikado-method` | 모든 크기, 트리 | 의존성이 불명확한 복잡한 리팩터링 |

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ parallel-change` | 나뭇잎 노드를 parallel-change로 안전하게 구현 |
| `+ strangler-fig` | 모듈 교체 진행도를 Mikado 트리로 추적 |
| `+ tdd-strict` | 각 나뭇잎 노드 구현에 TDD 사이클 적용 |
| `+ ouroboros` | 리팩터링 목표를 시드 스펙으로 결정화 후 Mikado |

## 안티패턴

- ❌ **되돌리지 않고 계속 구현** — 깨진 상태가 누적됨
- ❌ **전제조건 없이 blocked 상태 방치** — 왜 막혔는지 기록해야 다음에 재시도 가능
- ❌ **큰 노드 하나에 모든 것 집어넣기** — 나뭇잎 노드가 충분히 작아야 함
- ❌ **done 노드 수정** — 완료된 노드는 건드리지 않는다 (별도 노드 추가)
