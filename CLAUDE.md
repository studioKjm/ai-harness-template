# CLAUDE.md — AI Harness Template

This is the harness template repository itself.

## Project Overview

AI 에이전트 하네스 엔지니어링 + Ouroboros(명세 기반 개발) 통합 오픈소스 템플릿.
두 가지 버전: Lite(bash only) / Pro(Python enhanced).

## Rules

1. **Lite는 외부 의존성 없음** — bash/sed/grep만 사용. commands/agents는 마크다운
2. **Pro는 Python 3.11+** — pydantic, pyyaml, aiosqlite, rich, typer
3. **민감 데이터 제로** — API 키, JWT, DB URL, 비즈니스 로직 절대 포함 금지
4. **스택 자동 감지** — init.sh가 프로젝트 타입을 알아서 판단
5. **점진적 채택** — 전부 쓸 필요 없이 개별 컴포넌트 선택 가능

## Structure

- `init.sh` — Lite 설치 스크립트 (Harness + Ouroboros commands/agents + methodology dispatcher)
- `lib/` — 공유 유틸리티 (detect-stack, render-template, colors, **methodology.sh**)
- `templates/` — 프로젝트에 복사할 템플릿 파일
- `gates/` — CI/CD 게이트 스크립트 (check-boundaries, check-secrets, check-spec)
- `boundaries/` — Claude Code 권한 프리셋 + hooks
- `commands/` — Ouroboros 슬래시 커맨드 (interview, seed, run, evaluate, evolve, unstuck, pm) + `/methodology`
- `agents/` — 11개 에이전트 페르소나 정의
- `ouroboros/` — 시드 스펙 템플릿, 모호성 체크리스트
- `methodology/` — 플러그인 시스템 (스키마, 레지스트리, 상태 템플릿)
- `methodologies/` — 번들 메서드 플러그인 5종 (ouroboros, living-spec, parallel-change, bmad-lite, exploration)
- `feedback/` — 피드백 루프 도구
- `examples/` — 스택별 예시
- `pro/` — Pro 버전 (Python 엔진, CLI, hooks)
- `docs/` — 가이드 (methodology-guide.md, methodology-catalog.md, CODEBASE-GUIDE.md)

## Methodology System

하네스 코어는 **고정**. 메서드는 **플러그인**으로 사용자가 선택·조합.

```bash
/methodology list                           # 사용 가능한 메서드
/methodology use ouroboros                  # 단일 활성화
/methodology compose ouroboros bmad-lite    # 다중 조합
```

번들 5종: ouroboros (default) · living-spec · parallel-change · bmad-lite · exploration. 자세한 내용은 `docs/methodology-guide.md`, `docs/methodology-catalog.md`.
