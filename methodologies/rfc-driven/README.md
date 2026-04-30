# RFC-driven — Methodology Plugin

> 큰 변경은 코드 전 RFC. 페이퍼 트레일이 결정의 비대칭 정보를 줄임.

## 목적

큰 변경(아키텍처 리팩터, 새 의존성, breaking migration)은 **코드 작성 전에 결정 합의**가 필요. 합의 없이 진행하면:
- 외주 클라이언트와 충돌 — "왜 이걸 한 거죠?"
- 팀 내 갈등 — "왜 X 안 쓰고 Y 썼지?"
- 미래의 자기 — "당시에 뭐 고민했더라?"

RFC는 **결정의 페이퍼 트레일**. ADR보다 가볍고 풀 BMAD보다 작음.

## ADR과의 차이

| 항목 | ADR | RFC |
|-----|-----|-----|
| 시점 | 결정 후 (사후 기록) | 결정 전 (협의) |
| 형식 | 짧은 마크다운 (decision + consequences) | 구조화된 yaml (motivation/design/alternatives/drawbacks) |
| 검토 | 보통 1명 작성 | 다수 리뷰어 |
| 강제 | 없음 | 게이트가 큰 PR에 RFC 링크 요구 |

ADR이 "결정 사실 기록"이라면 RFC는 "결정 과정 기록".

## 활성화

```bash
/methodology compose ouroboros rfc-driven
```

prerequisites: 없음.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/rfc new <slug>` | 신규 RFC (draft) |
| `/rfc propose <id>` | draft → proposed (필수 필드 검증) |
| `/rfc accept <id>` | proposed → accepted (--decided-by, --rationale 필수) |
| `/rfc reject <id>` | proposed → rejected |
| `/rfc supersede <id> --by <new>` | accepted → superseded |
| `/rfc link <id>` | RFC가 관할하는 파일/모듈 등록 |
| `/rfc-link` | 작업 PR 파일을 RFC와 연결 |
| `/rfc list / show` | 목록 / 상세 |

## State Machine

```
[draft] → [proposed] → [accepted] → [superseded]
            ↓             ↑
        [rejected]    (더 새 RFC가 대체)
            ↓
       [draft]            (수정용 롤백)
```

| 상태 | 의미 |
|-----|-----|
| draft | 작성 중 |
| proposed | 리뷰 중 (불변. 편집 시 draft로 롤백) |
| accepted | 승인. 구현 가능 |
| rejected | 거절 (이유 기록) |
| superseded | 새 RFC로 대체됨 |

## propose 자동 검증

`/rfc propose` 실행 시 다음 검증:
- summary 비어있지 않음
- motivation 비어있지 않음
- design 비어있지 않음
- alternatives ≥ 2개 ("do nothing" 포함 권장)
- drawbacks ≥ 1개 (정직성 강제)

위반 시 차단. `--force`로 우회 가능 (history에 unmet_criteria 기록).

## 추가되는 게이트

| 게이트 | severity | 역할 |
|-------|---------|------|
| `check-rfc-required.sh` | warning (config로 blocking 가능) | 큰 변경(>500 LOC/파일 또는 >1000 total)에 RFC 링크 없으면 경고 |

게이트 설정 (`.harness/rfc-driven/config.yaml`):
- `rfc_required_threshold.per_file_loc`: 500 (기본)
- `rfc_required_threshold.total_loc`: 1000 (기본)
- `always_required_paths`: auth/, migrations/, payment/, package.json 등
- `always_exempt_paths`: tests/, docs/, *.md
- `on_violation`: warn (기본) | block

## 산출물

```
.harness/rfc-driven/
├── rfcs/
│   └── rfc-2026-04-30-eventbus-replacement.yaml
├── config.yaml                # 임계값 + 필수/면제 경로
└── .rfc-links.yaml            # file → rfc-id 매핑 (게이트 소비)
```

## 시나리오 예시

**이벤트 버스 교체 (in-process → Kafka)**

```bash
# 1. RFC 생성
/rfc new eventbus-replacement \
  --title "Replace in-process event bus with Kafka for cross-service events" \
  --authors jimin

# 2. yaml 편집 — summary, motivation, design, ≥2 alternatives, ≥1 drawback
#    예시:
#    motivation: |
#      Past 3 incidents (inc-2026-02-*, inc-2026-03-*) traced to
#      in-process event delivery losing messages on crash.
#    alternatives:
#      - title: "AWS SQS"
#        pros: [...]
#        cons: ["vendor lock"]
#      - title: "Do nothing"
#        cons: ["incident rate continues"]
#    drawbacks:
#      - "Migration period needs dual-write 4-6 weeks"
#      - "Team needs Kafka training"

# 3. propose — 자동 검증 통과 필요
/rfc propose rfc-2026-04-30-eventbus-replacement

# 4. 리뷰 후 accept (또는 reject)
/rfc accept rfc-2026-04-30-eventbus-replacement \
  --decided-by team-lead \
  --rationale "Aligned with Q3 OKR; ROI clear from incident pattern" \
  --conditions "Phase 1: non-critical events only; phase 2 after 60d soak"

# 5. RFC가 관할하는 파일 등록
/rfc link rfc-2026-04-30-eventbus-replacement \
  --files src/main.ts \
  --modules src/events/ src/messaging/

# 6. 구현 PR 작성. 큰 변경이라도 게이트 경고 없음 (RFC 링크 있음)

# 7. 6개월 뒤 v2 필요 시 supersede
/rfc accept rfc-2026-09-01-eventbus-v2 \
  --decided-by team-lead \
  --rationale "..."
/rfc supersede rfc-2026-04-30-eventbus-replacement \
  --by rfc-2026-09-01-eventbus-v2
# → 두 RFC의 links 자동 양방향 연결
```

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ ouroboros` | RFC의 design이 시드 input |
| `+ parallel-change` | RFC adoption_plan이 parallel-change plans 참조 |
| `+ strangler-fig` | 모듈 마이그레이션 RFC가 strangler plan 생성 |
| `+ bmad-lite` | RFC를 구현하는 stories는 RFC와 link |
| `+ exploration` | spike 결과가 RFC alternatives에 evidence |
| `+ incident-review` | incidents가 RFC motivation의 evidence |
| `+ threat-model-lite` | 보안 RFC에 linked threat model |
| `+ observability-first` | RFC design이 SLO target 명시 |

## 안티패턴

- ❌ **코드 작성 후 RFC** — ADR로 충분. 사후 RFC는 의미 없음
- ❌ **alternative 1개** ("아무것도 검토 안 함") — 게이트 차단
- ❌ **drawbacks 0개** — 모든 설계는 트레이드오프 있음
- ❌ **rationale: "approved"** — 실질적 추론 필요
- ❌ **모든 RFC를 수락** — RFC는 결정 도구. reject도 정상
- ❌ **mega-RFC로 모든 PR 커버** — 게이트 우회 목적이면 의미 없음
- ❌ **proposed 영원 정체** — 시간 박스 두고 결정 강제

## 한계 (v0.1)

- 리뷰어 자동 알림 없음 (Slack/email 연동은 v0.2)
- 정족수 강제 없음 (`required_approvals` 필드는 있으나 자동 검증 X)
- diagram 생성 없음 (yaml에 텍스트로만)
- RFC와 PR 자동 cross-link 없음 (수동 `/rfc link`)

## 진화 계획

| 버전 | 추가 |
|-----|------|
| v0.1 (현재) | 5-state, propose 검증, link/declare-pr, threshold 게이트 |
| v0.2 | Slack/GitHub 리뷰어 알림, 정족수 자동 검증, RFC ↔ PR 자동 연결 |
| v0.3 | 다이어그램 생성 (Mermaid), RFC 라이브러리 검색 |
