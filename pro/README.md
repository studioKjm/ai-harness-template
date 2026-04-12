# AI Harness Pro

**Harness + Ouroboros** = 명세 기반 개발 + 구조적 가드레일

Lite(bash only) 위에 Python 엔진을 얹어 실제 모호성 점수 계산, 온톨로지 수렴 추적, 3단계 자동 평가, 세션 영속성을 제공합니다.

## Lite vs Pro

| 기능 | Lite (bash) | Pro (Python) |
|------|:-----------:|:------------:|
| 하네스 게이트 (import/secret/structure) | O | O |
| 권한 프리셋 (strict/standard/permissive) | O | O |
| 스택 자동 감지 | O | O |
| 슬래시 커맨드 (interview/seed/run/evaluate) | O | O |
| 9개 에이전트 페르소나 | O | O |
| **실제 모호성 점수 계산** | - | O |
| **온톨로지 유사도 추적** | - | O |
| **3단계 자동 평가 파이프라인** | - | O |
| **세션 영속성 (SQLite)** | - | O |
| **드리프트 모니터링 훅** | - | O |
| **CLI 도구 (`harness` 커맨드)** | - | O |
| **키워드 감지 훅** | - | O |

## Install

```bash
# Prerequisites: Python 3.11+

# From the harness template repo:
./pro/install.sh /path/to/your-project
```

## CLI Usage

```bash
# Start interview
harness interview "알림 시스템을 만들고 싶어"

# Check ambiguity score
harness score

# Generate seed from interview
harness seed

# Run evaluation
harness evaluate

# Measure drift
harness drift src/notification.py

# Session status
harness status
```

## Architecture

```
your-project/
├── (Lite harness files)
├── .claude/
│   ├── commands/                 # Slash commands
│   │   ├── interview.md
│   │   ├── seed.md
│   │   ├── run.md
│   │   ├── evaluate.md
│   │   ├── evolve.md
│   │   ├── unstuck.md
│   │   └── pm.md
│   └── agents/                   # Agent personas
│       ├── interviewer.md
│       ├── ontologist.md
│       └── ...
└── .harness/
    ├── gates/
    │   ├── (Lite gates)
    │   └── check-spec.sh         # Spec completeness gate
    ├── pro-hooks/
    │   ├── keyword-detector.py
    │   ├── drift-monitor.py
    │   └── session-start.py
    └── ouroboros/
        ├── seeds/                # Immutable seed specs (YAML)
        ├── interviews/           # Interview records
        ├── evaluations/          # Evaluation results
        ├── scoring/
        │   └── ambiguity-checklist.yaml
        ├── templates/
        │   └── seed-spec.yaml
        └── session.db            # SQLite session store
```

## Python Package

```
pro/src/harness_pro/
├── cli.py              # Typer CLI
├── interview/
│   └── engine.py       # Interview with ambiguity tracking
├── scoring/
│   └── ambiguity.py    # Ambiguity formula engine
├── ontology/
│   └── extractor.py    # Ontology extraction & similarity
├── evaluation/
│   └── pipeline.py     # 3-stage verification
├── persistence/
│   └── store.py        # SQLite event store
└── drift/
    └── monitor.py      # Spec drift measurement
```
