# BMAD-lite — Methodology Plugin

> Persona-driven story decomposition — BMAD's persona discipline without heavy document machinery.

## 목적

기존 우로보로스(0→1 명세 우선)에 **페르소나 + 스토리 분해** 레이어를 얹는다. 풀 BMAD 처럼 PRD/Architecture Document 같은 무거운 문서 사이클은 도입하지 않고, BMAD의 핵심 가치 두 가지만 가져옴:

1. **명시적 페르소나 전환** — 같은 뇌, 다른 렌즈
2. **스토리 형식 강제** — pm-strict가 모호한 AC를 차단

```
[seed-v1 (ouroboros)]
        ↓
/persona analyst        → 도메인 엔티티/행위 추출
        ↓
/story new <slug>       → narrative + AC 작성
        ↓
/persona ux-designer    → UI/플로우 설계 (선택)
        ↓
/persona pm-strict      → AC 품질 검증
        ↓
verdict: pass           → status: refined
        ↓
/decompose <story-id>   → 태스크로 분해 (ouroboros)
```

## 활성화

```bash
/methodology compose ouroboros bmad-lite
```

prerequisites: seed-v1.yaml 존재. 즉 `/interview → /seed`가 먼저 끝나 있어야 함.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/persona <name>` | 페르소나 활성화 (analyst / ux-designer / pm-strict) |
| `/persona clear` | 기본 추론 모드로 복귀 |
| `/persona list` | 사용 가능한 페르소나 목록 |
| `/story new <slug>` | 새 스토리 작성 |
| `/story refine <id>` | 기존 스토리 재검증 (pm-strict 다시 통과) |
| `/story show <id>` | 스토리 출력 |
| `/story list [epic]` | 스토리 목록 |

## 페르소나 (3종)

| 이름 | 역할 | 출력 형식 |
|------|------|----------|
| **analyst** | 도메인 분석가 | `entities[]`, `behaviors[]`, `ambiguities[]` |
| **ux-designer** | UX 플로우 설계 | `flow`, `ui_primitives[]`, `state_coverage` |
| **pm-strict** | AC 품질 검증 | `verdict: pass\|block`, `issues[]` |

페르소나는 **추론 방식만 바꿈** — 도구 권한이나 게이트는 동일.

## 추가되는 게이트

| 게이트 | 심각도 | 역할 |
|-------|--------|------|
| `check-story-format.sh` | warning | narrative 누락, AC 없음, weasel words(fast/easy/secure 등) 경고 |

게이트는 차단하지 않음 — pm-strict가 인터랙티브하게 차단함.

## 산출물 위치

```
.harness/bmad-lite/
├── stories/
│   ├── st-2026-04-29-user-signup.yaml
│   └── st-2026-04-29-password-reset.yaml
├── epics/
│   └── ep-2026-04-29-auth-recovery.yaml
└── (active persona state)

.harness/state/bmad-lite.yaml         # active_persona, activated_at
```

## 시나리오 예시

**비밀번호 재설정 기능 (외주 SaaS의 신규 기능)**

```bash
# 0. 가정: seed-v1 이미 존재. 비밀번호 재설정 요구가 들어옴.

# 1. analyst 페르소나로 도메인 매핑
/persona analyst
# 사용자가 자연어로 요구사항 던짐 → analyst가 entities/behaviors 정리
# → "ResetToken 엔티티가 seed에 없음. seed-v2로 갈지, pending 처리할지 결정 필요"

# 2. seed 갱신 (필요시)
#    /interview 한 라운드 → /seed (v2)

# 3. 스토리 작성
/story new password-reset
# narrative + AC 입력 (analyst 출력 자동 반영됨)

# 4. UX 페르소나로 플로우 설계
/persona ux-designer
# → flow: 이메일 입력 → 토큰 발송 → 링크 클릭 → 새 비밀번호 입력
# → states_handled: empty/loading/success/error/expired-token

# 5. pm-strict로 검증
/persona pm-strict
/story refine st-2026-04-29-password-reset
# → verdict: block, "AC-2: '빠르게' 단어 사용. 메트릭 명시 필요"
# → narrative 또는 AC 수정 후 재검증

# 6. pass 시 status: refined
# 7. 태스크 분해 (ouroboros 흐름으로 복귀)
/decompose st-2026-04-29-password-reset
```

## BMAD와의 차이 (의도적)

| BMAD 풀 사이클 | BMAD-lite |
|---------------|-----------|
| Analyst → PM → Architect → SM → Dev → QA (6 페르소나) | analyst / ux-designer / pm-strict (3) |
| PRD, Architecture Doc, Front-end Spec | 스토리 + 에픽 YAML만 |
| Web AI (planning) + IDE AI (dev) 2-phase | 단일 IDE 흐름 |
| Story = 100-200 lines markdown | Story = 50-line YAML |
| Brownfield 전용 분기 있음 | seed 기반 → 브라운필드는 living-spec 영역 |

**BMAD의 강점은 페르소나 디시플린**. 무거운 문서·역할 분리는 1인 ~ 소규모 외주에 오버킬 → 그 부분 제거.

## Living Spec과 조합

```bash
/methodology compose ouroboros bmad-lite living-spec
```

- seed-v2로 갈 때 → living-spec의 `/diff-spec`이 변경 감지
- 기존 스토리들은 → bmad-lite가 `superseded_by` 필드로 폐기 추적
- 신규 스토리는 → analyst 페르소나로 신규 엔티티만 매핑

## Parallel Change와 조합

```bash
/methodology compose ouroboros bmad-lite parallel-change
```

- AC가 breaking change면 → pm-strict가 "/parallel-change new를 먼저 만드세요" 권고
- 스토리 status는 ready로 가지만 → parallel-change plan이 contract phase 도달해야 done 가능

## 한계 (v0.1)

- 페르소나는 추론 스타일만 바꿈 — 실제 LLM 라우팅이나 도구 차단 없음
- pm-strict의 weasel word 탐지는 정적 패턴 — 문맥 무시
- ux-designer가 코드베이스 스캔해서 기존 컴포넌트 추천하는 기능은 v0.2

## 진화 계획

| 버전 | 추가 |
|-----|------|
| v0.1 (현재) | 3 페르소나, 스토리/에픽 템플릿, format warning 게이트 |
| v0.2 | ux-designer가 기존 컴포넌트 자동 스캔, pm-strict 문맥 인지 |
| v0.3 | architect 페르소나 추가 (선택), Brownfield 통합 |

## 안티패턴 (이건 BMAD-lite로 하지 마세요)

- ❌ 0→1 신규 프로젝트의 첫 스펙 작업 → `/interview → /seed` (ouroboros) 사용
- ❌ DB/API breaking change → `/parallel-change` (parallel-change) 사용
- ❌ 단순 버그 수정 → 그냥 `/decompose` 단독 사용
- ❌ 6명 이상 팀의 풀 BMAD가 필요한 상황 → BMAD 본가 사용 (https://github.com/bmadcode/BMAD-METHOD)
