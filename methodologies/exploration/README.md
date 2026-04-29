# Exploration — Methodology Plugin

> Time-boxed spikes for learning before committing to a spec.

## 목적

명세 우선(ouroboros), 스토리 우선(BMAD-lite) 방법론은 **무엇을 만들지 알 때** 강하다. 그러나 종종:

- 어떤 라이브러리·API가 실제 동작하는지 모름
- 새 인프라(엣지 런타임, 벡터 DB 등) 검증 필요
- 스펙 작성 자체가 막혔는데 기술 미지수가 원인

이때 **시간 박스를 둔 스파이크**를 따로 분리한다. 본체 코드 트리와 격리된 sandbox에서 일하되, **샌드박스 내부는 layer/spec/structure 게이트가 풀린다** — 그게 spike의 핵심이기 때문.

```
[questioning] → [spiking] → [learned] → [applied]
       │            │           │
       └────────────┴───────────┴─────→ [abandoned]
```

## 활성화

```bash
/methodology compose ouroboros exploration
# 또는 단독
/methodology use exploration
```

prerequisites: 없음. 어떤 시점에도 사용 가능 (`/interview` 이전 포함).

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/spike new <slug> --question "..."` | 신규 스파이크 (question + timebox 강제) |
| `/spike start <id>` | questioning → spiking (타임박스 시작) |
| `/spike close <id> --learning-id ...` | spiking → learned (학습 기록 필수) |
| `/spike apply <id>` | learned → applied (ADR/seed/code 승격 후) |
| `/spike abandon <id> --reason ...` | 어느 단계에서든 폐기 (사유 기록) |
| `/spike list [--status ...]` | 스파이크 목록 |
| `/spike show <id>` | 스파이크 상세 |
| `/learn record <spike-id>` | 발견 사항 기록 (learning.yaml 생성) |
| `/learn promote <id> --to adr\|seed\|code` | 학습을 영속 산출물로 승격 |
| `/learn list` | 학습 목록 + 승격 상태 |

## 게이트 완화 (Relaxation)

스파이크의 핵심: **샌드박스 내부는 통상 게이트가 적용되지 않음**.

| 완화 대상 | 경로 패턴 | 이유 |
|----------|---------|------|
| `boundaries` | `.harness/exploration/spikes/<id>/sandbox/**` | 레이어 경계 무시 — 빠른 검증이 목적 |
| `spec` | 동일 | seed에 묶이지 않음 |
| `structure` | 동일 | 자유 구조 |

**여전히 작동하는 게이트** (절대 끄지 않음):
- `secrets` — 비밀키 노출은 어디든 차단
- `security` — SAST는 어디든 작동

샌드박스 코드는 **버려질 코드**라는 전제. 살아남으려면 본체 트리로 복사 후 게이트 통과 필요.

## 산출물

```
.harness/exploration/
├── spikes/
│   └── sp-2026-04-29-llm-streaming/
│       ├── spike.yaml              # 메타데이터 + state
│       └── sandbox/                # 게이트 완화 영역 — 자유 코드
│           └── ... (실험 코드)
├── learnings/
│   └── ln-2026-04-29-llm-streaming.yaml   # 발견 + 증거 + 권고 + 적용처
└── .gate-relaxation.yaml           # 게이트 컨슈머 컨트랙트 (자동 생성)

.harness/state/exploration.yaml      # 메서드 활성 상태
```

## 시나리오 예시

**LLM 스트리밍 검증 (ouroboros 스토리가 막힌 경우)**

```bash
# 0. 가정: 스토리 "AI 채팅" 작성 중. Vercel Edge에서 OpenAI 스트리밍이
#    실제로 가능한지 모름. → 스파이크.

# 1. 스파이크 생성
/spike new llm-streaming-vercel \
  --question "Vercel Edge에서 OpenAI 토큰 스트리밍 TTFT가 300ms 미만인가?" \
  --timebox 4 \
  --hypothesis "AI SDK + Edge runtime 조합이면 가능"

# 2. 타임박스 시작
/spike start sp-2026-04-29-llm-streaming-vercel

# 3. sandbox/ 디렉토리에서 자유롭게 실험
#    (boundaries/spec/structure 게이트 안 걸림)
echo 'export const runtime = "edge"' > .harness/exploration/spikes/sp-2026-04-29-llm-streaming-vercel/sandbox/test.ts
# ... 실험 코드 ...
# ... 측정 ...

# 4. 학습 기록
/learn record sp-2026-04-29-llm-streaming-vercel
# → ln-2026-04-29-llm-streaming-vercel.yaml 생성
#   finding.summary: "TTFT 평균 220ms, p95 280ms — 가능"
#   evidence: 측정 로그 첨부
#   recommendation.action: adopt

# 5. 스파이크 종료
/spike close sp-2026-04-29-llm-streaming-vercel \
  --learning-id ln-2026-04-29-llm-streaming-vercel

# 6. ADR로 승격 (의사결정으로 영속화)
/learn promote ln-2026-04-29-llm-streaming-vercel \
  --to adr --target ADR-014

# 7. 스파이크 applied
/spike apply sp-2026-04-29-llm-streaming-vercel

# 8. 막혀있던 스토리로 복귀 — 이제 AC 확정 가능
```

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ ouroboros` | 학습이 새 `seed-vN`을 정당화하는 evidence_source가 됨 |
| `+ living-spec` | 스파이크가 "seed 진화가 맞는가?"를 답함 |
| `+ BMAD-lite` | 스파이크 학습이 `analyst.ambiguities`를 해소 → 스토리 refined 가능 |
| `+ parallel-change` | 스파이크가 breaking change 후의 실제 동작을 사전 검증 |

## 안티패턴 (이걸 spike라고 부르지 마세요)

- ❌ "한 번만 빠르게 짜보자" — timebox 없으면 스파이크 아님
- ❌ "이걸 production에 그대로 넣자" — 샌드박스 코드는 버린다는 전제
- ❌ 학습 기록 없이 spike close — 기록 안 하면 반복됨
- ❌ 스파이크 "applied" 직후 ADR/seed 업데이트 안 하기 — 학습이 휘발

## 한계 (v0.1)

- 타임박스 자동 강제 (kill) 없음 — soft warning만
- 게이트 컨슈머가 `.gate-relaxation.yaml`을 읽도록 업데이트되어야 실효 발생 (v0.2에서 boundaries 게이트부터 적용 예정)
- 학습 간 의존성 그래프 미지원 (`related.prior_learnings`는 수동 입력)

## 진화 계획

| 버전 | 추가 |
|-----|------|
| v0.1 (현재) | 4-state 머신, 샌드박스 분리, 학습 → ADR/seed 승격 |
| v0.2 | boundaries / structure 게이트가 `.gate-relaxation.yaml` 자동 소비 |
| v0.3 | 타임박스 만료 시 자동 알림, 학습 그래프 시각화 |

## 컨슈머 컨트랙트 (게이트 작성자 참고)

자기 게이트가 exploration의 완화를 존중하게 하려면:

```bash
# 게이트 스크립트 시작부에:
RELAX_FILE=".harness/exploration/.gate-relaxation.yaml"
if [[ -f "$RELAX_FILE" ]]; then
    # python3로 자기 target("boundaries" 등)에 매치되는 paths 추출
    # 매치되는 파일은 검사 스킵
fi
```

자세한 스키마는 `scripts/sync-relaxation.py` 헤더 참조.
