# TDD Strict — Methodology Plugin

> Red → Green → Refactor — test-first enforced by git history gate.

## 목적

**테스트 우선 작성**을 관례가 아닌 게이트로 강제. 소스 파일이 테스트 파일보다 git 히스토리에 먼저 등장하면 커밋을 차단.

```
[요구사항 확정]
     ↓
/tdd new <target>      — 사이클 생성 (상태: 🔴 red)
     ↓
테스트 작성 → git add test → git commit   ← 게이트 통과
     ↓
소스 작성 → git add source → git commit  ← 게이트: test가 먼저인지 검증
     ↓
/tdd pass <id>         — 상태: 🟢 green
     ↓
리팩터링 → [refactor] 커밋                 ← 게이트 면제 (prefix 기반)
     ↓
/tdd refactor <id>     — 상태: 🔵 refactor
     ↓
/tdd done <id>         — 상태: ✅ done
```

## 활성화

```bash
/methodology use tdd-strict
```

requires: 없음. 단독 또는 ouroboros와 조합.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/tdd new` | 새 TDD 사이클 시작 |
| `/tdd pass` | 테스트 통과 확인 (red → green) |
| `/tdd refactor` | 리팩터 단계 진입 (green → refactor) |
| `/tdd done` | 사이클 완료 |
| `/tdd status` | 사이클 상태 확인 |
| `/tdd list` | 전체 사이클 목록 |
| `/tdd-config` | 페어링 컨벤션 설정 |

## 게이트 — check-test-first.sh

**blocking** 게이트. `pre-commit` 시점에 실행.

검증 내용:
1. 스테이징된 소스 파일에 대응하는 테스트 파일이 git 히스토리에 존재하는가
2. 테스트 파일의 첫 커밋 타임스탬프가 소스 파일보다 이른가

면제 조건:
- 커밋 메시지 prefix: `[refactor]`, `[chore]`, `[docs]`, `[style]`, `[ci]`, `[infra]`
- 설정된 exempt_dirs / exempt_patterns
- 테스트 파일 자체 (항상 통과)

## 산출물

```
.harness/tdd-strict/
├── cycles/tdd-YYYYMMDD-NNN.yaml   # 사이클별 상태
├── config.yaml                    # 페어링 컨벤션
└── ...
.harness/state/tdd-strict.yaml
```

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ ouroboros` | 시드 AC → TDD 사이클 1:1 매핑 |
| `+ parallel-change` | Expand/Migrate/Contract 각 단계마다 TDD 사이클 |
| `+ lean-mvp` | Hypothesis → TDD 사이클 → Measure |
| `+ observability-first` | SLO 검증 코드도 test-first |

## 안티패턴

- ❌ 소스 먼저 커밋하고 나중에 테스트 — 게이트 차단
- ❌ 테스트와 소스를 같은 커밋 (`allow_same_commit: false` 기본값)
- ❌ 리팩터링에 `[refactor]` prefix 없이 커밋 후 소스 변경 — gate 잘못 면제
- ❌ 녹색 만들기 위한 과도한 구현 — 최소 구현 원칙 위반
