# /bdd — BDD Scenario Command

Given/When/Then 시나리오를 작성하고 구현 상태를 추적합니다.

## Usage

```
/bdd new <title> [--feature|-f <FTR-ID>]
/bdd list [--state|-s <state>] [--feature|-f <FTR-ID>]
/bdd show <SCN-ID>
/bdd status <SCN-ID> <state>
/bdd link <SCN-ID> [--tdd <TDD-ID>] [--story <story-id>] [--rfc <RFC-ID>]
```

## States

```
draft → ready → implementing → passing
                             ↘ skipped
```

| State | 의미 |
|-------|------|
| `draft` | 시나리오 작성 중 |
| `ready` | Given/When/Then 완성, 구현 준비 |
| `implementing` | TDD 사이클과 연결, 구현 중 |
| `passing` | 테스트 통과 확인 |
| `skipped` | 범위 외 또는 향후 구현 예정 |

## Workflow

```
1. /bdd new "고객이 상품을 장바구니에 추가할 수 있다"
2. # .harness/bdd/scenarios/SCN-20260501-001-고객이-상품을.yaml 편집
3. /bdd status SCN-001 ready
4. /bdd link SCN-001 --tdd TDD-20260501-001   # TDD 사이클 연결
5. /bdd status SCN-001 implementing
6. # 구현 완료 후
7. /bdd status SCN-001 passing
```

## BDD 3 Amigos

시나리오 작성 전 세 가지 관점 확인:
- **Product (기획)**: "어떤 문제를 해결하나?"
- **Dev (개발)**: "어떻게 구현하나?"
- **QA (테스트)**: "어떻게 검증하나?"

## Given/When/Then 작성 규칙

```yaml
# ✅ 좋은 예 — 구체적이고 단일 행동
given:
  - "고객 계정이 존재한다"
  - "장바구니가 비어있다"
when:
  - "고객이 상품 ID 'PROD-001'을 장바구니에 추가한다"
then:
  - "장바구니에 상품이 1개 있다"
  - "장바구니 총액이 10,000원이다"

# ❌ 나쁜 예 — 너무 광범위
given:
  - "시스템이 준비되어 있다"
when:
  - "사용자가 모든 것을 한다"
then:
  - "잘 된다"
```

## Composition

```
/methodology compose bdd tdd-strict    # 시나리오 → TDD 사이클로 세분화
/methodology compose bdd ddd-lite      # Feature = Bounded Context 단위
/methodology compose bdd living-spec   # 시나리오가 살아있는 명세의 일부
```
