# /ddd — DDD Lite Command

Domain-Driven Design 핵심 산출물(Bounded Context, Aggregate, Domain Event, Glossary)을 관리합니다.

## Usage

```
/ddd context new <name> [--description|-d <desc>] [--owner|-o <owner>]
/ddd context list
/ddd context show <BC-ID>

/ddd aggregate new <name> [--context|-c <BC-ID>] [--description|-d <desc>]
/ddd aggregate list

/ddd event new <name> [--context|-c <BC-ID>] [--aggregate|-a <AGG-ID>]

/ddd glossary add <term> [--context|-c <BC-ID>] [--definition|-d <def>]
/ddd glossary list [--context|-c <BC-ID>]

/ddd tree          # 컨텍스트 맵 출력
```

## Workflow

```
1. /ddd context new OrderManagement --owner "주문팀"
2. /ddd aggregate new Order --context BC-20260501-001
3. /ddd event new OrderPlaced --aggregate AGG-20260501-001
4. /ddd glossary add "주문" --context BC-20260501-001 --definition "고객이 상품을 구매 요청한 단위"
5. /ddd tree   # 전체 컨텍스트 맵 확인
```

## Bounded Context States

| State | 의미 |
|-------|------|
| `draft` | 정의 중 — 경계가 아직 확정되지 않음 |
| `active` | 운영 중 — 게이트가 이 경계를 강제 |
| `deprecated` | 폐기 예정 — strangler-fig로 교체 중 |

## DDD 핵심 개념

| 개념 | 설명 |
|------|------|
| **Bounded Context** | 도메인 모델이 통용되는 경계. 같은 단어도 컨텍스트마다 의미가 다를 수 있음 |
| **Aggregate** | 트랜잭션 일관성 경계. Root를 통해서만 외부 접근 허용 |
| **Domain Event** | 과거형 동사 — 비즈니스적으로 의미 있는 사건 (OrderPlaced, PaymentFailed) |
| **Ubiquitous Language** | 개발자·도메인 전문가가 공유하는 용어집. 코드와 대화가 동일한 언어를 씀 |

## Integration Patterns (컨텍스트 간 통합)

| 패턴 | 상황 |
|------|------|
| `shared-kernel` | 두 팀이 공유 코어 공동 소유 |
| `customer-supplier` | 하위 팀이 상위 팀 요구사항에 맞춤 |
| `conformist` | 외부 모델을 그대로 수용 |
| `anticorruption-layer` | 외부 모델에서 내부 모델로 변환 레이어 |
| `open-host` | 프로토콜/API 공개 (소비자가 직접 붙음) |
| `published-language` | 공개된 교환 언어 (JSON Schema, Protobuf 등) |

## Composition

```
/methodology compose ddd-lite tdd-strict     # Aggregate 불변조건 → TDD 사이클
/methodology compose ddd-lite bdd            # Bounded Context → Feature/Scenario
/methodology compose ddd-lite strangler-fig  # 컨텍스트 분리 → 점진적 교체
```
