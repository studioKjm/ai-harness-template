# Strangler Fig — Methodology Plugin

> 레거시 모듈을 facade로 감싸 점진적으로 새 모듈로 교체.

## 목적

전체 재작성은 너무 위험하고, 단일 함수 변경(`parallel-change`)으로는 부족한 **모듈·시스템 단위 마이그레이션**을 위한 방법론.

- 기존 모듈(legacy) 옆에 새 모듈(new)과 라우터(facade)를 둠
- facade가 라우팅 룰에 따라 트래픽을 legacy 또는 new로 분기
- 룰을 하나씩 new로 옮기며 점진 컷오버
- 100% 새 모듈로 전환되면 legacy 삭제

```
[legacy-only] → [coexist] → [new-primary] → [retired]
                    ↓             ↓
              [legacy-only]  [coexist]    (롤백 허용)
```

## parallel-change와의 차이

| 항목 | parallel-change | strangler-fig |
|-----|----------------|---------------|
| 단위 | 함수·시그니처 | 모듈·시스템 |
| 상태머신 | expand/migrate/contract | legacy-only/coexist/new-primary/retired |
| 기간 | 보통 며칠~몇 주 | 보통 몇 주~몇 달 |
| caller 추적 | grep 기반 정적 | 라우팅 룰 명시 |
| 게이트 | 2 blocking | 1 warning |
| 전형 케이스 | `Refund.amount: number → enum` | "2018년 빌링 모듈을 v2 아키텍처로 교체" |

둘은 **함께 쓸 수 있음**. 큰 모듈 strangler 안에서 작은 함수 깨짐은 parallel-change로.

## 활성화

```bash
/methodology compose ouroboros strangler-fig
# 또는 (greenfield+legacy 혼재 프로젝트)
/methodology compose ouroboros bmad-lite strangler-fig
```

prerequisites: 없음. 클라이언트 레거시 인수 직후에도 사용 가능.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/strangler new <slug>` | 신규 plan (legacy/new/facade 경로 명시) |
| `/strangler list [--state ...]` | plan 목록 + 커버리지 |
| `/strangler show <id>` | plan 상세 (라우팅 룰, 커버리지, 히스토리) |
| `/strangler advance <id> <state>` | state 전이 (cutover criteria 자동 검증) |
| `/strangler-route add <id> --pattern PAT --target new\|legacy` | 라우팅 룰 추가 |
| `/strangler-route remove <id> --rule-id RID` | 라우팅 룰 삭제 |
| `/strangler-retire <id>` | 최종 폐기 (legacy 삭제 직전 게이트) |

추가 유틸:
```bash
# 레거시 모듈 디렉토리 grep으로 HTTP 엔드포인트 자동 수집
python3 .harness/methodologies/strangler-fig/scripts/sf.py coverage <id> \
  --scan-endpoints "src/legacy/**/*.ts"
```

## State별 cutover criteria (자동 검증)

| 목표 state | 자동 체크 |
|----------|---------|
| coexist | facade.exists_yet=true · ≥1 routing rule · new_module.exists_yet=true |
| new-primary | ≥80% rules → target new |
| retired | 모든 rules → target new · coverage 100% |

수동 체크(템플릿에 명시, 자동 X):
- "production 사고 없음 (지난 14일)"
- "성능 패리티 검증 (legacy 대비 p95 ±20%)"
- "롤백 플랜 문서화"

`--force`로 자동 검증 우회 가능 (history에 기록 + unmet_criteria 보존).

## 산출물

```
.harness/strangler-fig/
└── plans/
    └── sf-2026-04-30-billing-rewrite.yaml   # legacy/new/facade 경로,
                                              # 라우팅 룰, 커버리지, 히스토리
```

## 시나리오 예시

**클라이언트 인수: 2018년 빌링 모듈 → v2 아키텍처**

```bash
# 1. plan 생성
/strangler new billing-rewrite \
  --legacy "src/legacy/billing/" \
  --new "src/billing/" \
  --facade "src/billing-facade/" \
  --title "Replace 2018 billing with v2"

# 2. 레거시 엔드포인트 자동 스캔
python3 .harness/methodologies/strangler-fig/scripts/sf.py \
  coverage sf-2026-04-30-billing-rewrite \
  --scan-endpoints "src/legacy/billing/**/*.ts"
# → 수십 개 엔드포인트 추출됨

# 3. facade + 첫 번째 rule
# (코드: facade 만들고 새 모듈에 첫 핸들러 구현)
/strangler-route add sf-2026-04-30-billing-rewrite \
  --pattern "POST /api/refunds" --target new \
  --reason "v2 RefundService — bit-for-bit equivalence test passed"

# 4. legacy-only → coexist
/strangler advance sf-2026-04-30-billing-rewrite coexist
# → cutover criteria 자동 검증 (facade.exists_yet, ≥1 rule, new_module.exists_yet)

# 5. (수 주~수 달) 룰을 new로 옮기며 점진 cutover
# 매 룰 추가 시 production 모니터링 → 안정 확인 → 다음 룰

# 6. coexist → new-primary (≥80% new)
/strangler advance sf-2026-04-30-billing-rewrite new-primary

# 7. 마지막 edge cases 처리. 전체 100% new.

# 8. 30일 무트래픽 확인 후 retire
/strangler-retire sf-2026-04-30-billing-rewrite

# 9. 별도 commit으로 legacy 디렉토리 삭제
rm -rf src/legacy/billing/
git commit -m "chore: remove legacy billing module (sf plan retired)"
```

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ ouroboros` | 새 모듈 설계는 시드 기반 |
| `+ parallel-change` | 새 모듈 안의 함수 시그니처 변경은 parallel-change로 |
| `+ exploration` | 레거시 분석·아키텍처 검증 spike → 학습 → strangler 시작 |
| `+ bmad-lite` | 라우팅 결정에 UX 영향 있을 때 (예: URL 구조 변경) story로 |
| `+ living-spec` | 새 모듈의 시드가 진화하면 라우팅 룰 영향 추적 |

## 안티패턴

- ❌ **Legacy에 신규 코드 추가** — strangling 도중 legacy가 자라면 끝나지 않음. coexist 진입 직후 legacy 디렉토리 lock 권장
- ❌ **Facade 영구화** — retire 후 facade 단순화 안 하면 dead routing logic 누적
- ❌ **30일 quiet period 스킵 후 retire** — 캐시된 클라이언트가 여전히 legacy 호출 가능
- ❌ **단일 commit에 retire + delete** — 롤백 불가능. 항상 분리

## 한계 (v0.1)

- 라우팅 룰 패턴은 free-form 문자열 — 실제 facade가 어떻게 해석하는지는 사용자 책임
- 트래픽 측정 자동화 없음 — "legacy 호출 0건" 검증은 외부 APM/log에서 수동
- AST 기반 caller 분석 없음 — endpoint 스캔은 grep heuristic
- 한 plan 안의 patterns는 `unique` 강제, plan 간 충돌은 미검증

## 진화 계획

| 버전 | 추가 |
|-----|------|
| v0.1 (현재) | 4-state machine, routing rules, coverage tracking, 1 warning gate |
| v0.2 | APM 연동 (legacy traffic 0건 자동 검증), AST 기반 caller 분석 |
| v0.3 | 대시보드 (전체 plans 진행률 시각화), feature flag 시스템 통합 |
