# /ddd-glossary — Ubiquitous Language Glossary

팀 전체가 공유하는 도메인 용어집을 관리합니다. 코드의 클래스/함수명과 대화의 언어가 일치하도록 강제합니다.

## Usage

```
/ddd-glossary add <term> [--context|-c <BC-ID>] [--definition|-d <def>]
/ddd-glossary list [--context|-c <BC-ID>]
/ddd-glossary show <term>
```

## 왜 Ubiquitous Language가 중요한가

```
❌ 나쁜 예:
  - 기획서: "고객이 장바구니에 담는다"
  - DB 테이블: cart_items
  - 코드 클래스: ShoppingBasket
  - API: POST /orders/pending

  → 4가지 언어가 모두 다름 — 대화할 때마다 번역 비용 발생

✅ 좋은 예:
  - 기획서: "고객이 장바구니에 담는다"
  - DB 테이블: cart_items
  - 코드 클래스: Cart
  - API: POST /cart/items
  - 용어집: Cart = "고객이 주문 전 상품을 임시 보관하는 컨테이너"
```

## Tips

- `disputed` 상태: 팀 내 용어 합의가 안 된 경우 표시 → 정기 용어 리뷰 세션 필요
- `cross_context`: 같은 개념이 다른 컨텍스트에서 다른 이름일 때 명시 (예: Order ↔ Purchase)
- `synonyms`: 쓰면 안 되는 대체 표현 목록 (코드 리뷰에서 잡을 수 있도록)
