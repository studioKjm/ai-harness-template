# Ouroboros — Methodology Plugin (Default)

> 명세 우선 — Ambiguity ≤ 0.2까지 인터뷰 반복. 시드 스펙은 불변.

## 목적

0→1 신규 프로젝트의 **명세 결정화**. 코드 작성 전에 요구사항을 명확히 결정하고, 결정된 명세는 불변(시드)으로 보존. 변경은 새 버전(v1 → v2)으로만 가능.

```
[모호한 요구]
    ↓
/interview → Ambiguity 점수 측정 → ≤ 0.2까지 반복
    ↓
/seed → 불변 시드 생성 (seed-v1.yaml)
    ↓
/decompose → 시드를 원자 태스크로 분해
    ↓
/trd → 기술 요구사항 문서
    ↓
/run → Double Diamond 실행 (Discover/Define/Design/Deliver)
    ↓
/evaluate → 3단계 검증 (Mechanical/Semantic/Judgment)
    ↓
/evolve → Wonder/Reflect/Re-seed 루프
```

## 활성화

```bash
/methodology use ouroboros
```

prerequisites: 없음. 기본 메서드(default).

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/interview` | Socratic 요구사항 인터뷰 (Ambiguity ≤ 0.2 통과 기준) |
| `/seed` | 인터뷰 결과를 불변 명세로 결정화 |
| `/decompose` | 시드를 레이어 태그 포함 원자 태스크로 분해 |
| `/trd` | Technical Requirements Document 작성 |
| `/run` | Double Diamond 실행 (Pair Mode 옵션 — v2.1.0+) |
| `/evaluate` | 3단계 검증 (Mechanical → Semantic → Judgment) |
| `/evolve` | 학습 통합 + 시드 진화 루프 |

기타 (`/unstuck`, `/pm` 등)은 ouroboros 외부에서도 사용 가능 (코어 도구).

## 검증 단계 — Ambiguity 점수

`/interview` 통과 기준: **Ambiguity ≤ 0.2**.

체크리스트 (`.harness/ouroboros/scoring/ambiguity-checklist.yaml`):
- 사용자/액터 명확
- 입력/출력 명확
- 성공/실패 조건 측정 가능
- 경계/제약 명시
- 우선순위 결정됨

→ 점수 > 0.2면 다음 라운드 인터뷰 강제.

## 시드 스펙 — 불변성 원칙

```
.harness/ouroboros/seeds/
├── seed-v1.yaml     # 불변. 한 번 생성되면 수정 금지.
├── seed-v2.yaml     # 변경 시 새 버전 (living-spec 메서드와 조합)
└── ...
```

**시드 스펙 = 결정의 동결**. 변경하려면:
1. 새 인터뷰 라운드
2. 새 버전 (`seed-v2.yaml`) 생성
3. (선택) `living-spec` 메서드로 diff + 태스크 마이그레이션

## 산출물

```
.harness/ouroboros/
├── seeds/seed-vN.yaml
├── interviews/<topic>-<round>.yaml
├── tasks/<task-id>.yaml
├── evaluations/<task-id>-<stage>.yaml
└── trd/<id>.md
```

## 다른 메서드와의 조합

대부분의 메서드가 ouroboros를 base로 함:

| 조합 | 효과 |
|-----|------|
| `+ bmad-lite` | 시드 위에 페르소나·스토리 레이어 |
| `+ living-spec` | seed-v1 → v2 진화 추적 |
| `+ parallel-change` | 시드의 breaking change를 함수 레벨로 안전 마이그레이션 |
| `+ exploration` | 시드 작성이 막히면 spike → 학습 → 시드 |
| `+ rfc-driven` | accepted RFC가 시드 input |
| `+ threat-model-lite` | 보안 위협이 시드 AC 정당화 |
| `+ observability-first` | SLO target이 시드 AC ("system MUST achieve 99.5%") |

## 안티패턴

- ❌ **인터뷰 스킵하고 바로 코드** — Ambiguity 점수 우회. 명세 우선의 핵심 위반
- ❌ **시드 직접 수정** — 새 버전 생성 원칙 위반. 결정 동결 깨짐
- ❌ **인터뷰 1라운드로 종료** — Ambiguity ≤ 0.2 도달 전엔 다음 라운드 필수
- ❌ **단순 버그 수정에 ouroboros 풀 사이클** — 게이트만 작동시키고 ouroboros 비활성화

## 한계

- Ambiguity 점수는 휴리스틱 — 자동 평가 불완전
- 인터뷰 라운드는 사람이 진행 (LLM 보조 가능, 자동화는 v0.2)
- 시드 자동 마이그레이션은 living-spec 메서드 조합 필요

## 관련 문서

- 시드 스키마: `.harness/ouroboros/seeds/_schema/`
- Ambiguity 체크리스트: `.harness/ouroboros/scoring/ambiguity-checklist.yaml`
- Double Diamond 실행 패턴: `commands/run.md`
- 3단계 검증 규칙: `commands/evaluate.md`
- 진화 루프 설계: `commands/evolve.md`
