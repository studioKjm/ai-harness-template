# Threat Model (Lite) — Methodology Plugin

> 스토리·기능 작성 시점에 STRIDE 위협 분석. 사후 보안 패치 대신 설계 단계 차단.

## 목적

기존 하네스 코어의 `check-secrets.sh`/`check-security.sh`는 **이미 코드에 들어간 것**을 검증함 (사후). threat-model-lite는 **스토리·스펙 작성 시점**에서 위협을 식별하고 mitigation을 설계 (사전).

```
[스토리 작성] → trigger 매치 → /threat new → STRIDE 분석 → 리뷰 → 승인 → 구현
                                    ↓
                              security-reviewer 페르소나 가능
```

## 풀 STRIDE/DREAD와 차이

| 풀 STRIDE/DREAD | threat-model-lite |
|----------------|-------------------|
| 6 카테고리 + 5 점수 (Damage/Reproducibility/Exploitability/Affected/Discoverability) | 6 카테고리 + likelihood/impact만 |
| 별도 워크숍 | 스토리 작성 시점 inline |
| 위협 매트릭스 문서 | yaml 파일 |
| 보안 전문가 필수 | security-reviewer 페르소나 + LLM 보조 |

**lite의 의미**: 1인 ~ 소규모 팀이 매 스토리에 적용 가능한 수준으로 축소.

## 활성화

```bash
/methodology compose ouroboros bmad-lite threat-model-lite
# 또는 단독 (기존 코드의 보안 audit 시작할 때)
/methodology use threat-model-lite
```

prerequisites: 없음. 어느 시점이든 사용 가능.

## 제공 명령

| 명령 | 역할 |
|-----|------|
| `/threat new <slug>` | 신규 모델 (story/spike/feature/endpoint/module 대상) |
| `/threat add <id>` | STRIDE 카테고리에 위협+mitigation 추가 |
| `/threat review <id>` | draft → reviewed (STRIDE 커버리지 검증) |
| `/threat approve <id>` | reviewed → approved |
| `/threat apply <id>` | approved → applied (모든 mitigation 'implemented' 필수) |
| `/threat link <id>` | story/spike/ADR/incident와 연결 |
| `/threat scan` | 코드베이스 스캔 → 모델 없는 sensitive 파일 |
| `/threat list / show` | 목록 / 상세 |
| `/threat-triggers show / add` | 트리거 키워드·경로 관리 |

## STRIDE 카테고리

| 글자 | 영역 | 예시 위협 |
|-----|-----|---------|
| **S** | Spoofing (위장) | 자격증명 도용, 세션 하이재킹, 이메일 위장 |
| **T** | Tampering (변조) | 데이터 수정, 파라미터 조작 |
| **R** | Repudiation (부인) | 사용자가 행위 부정, 감사 로그 누락 |
| **I** | Information Disclosure (정보 노출) | 데이터 유출, IDOR, 사이드채널 |
| **D** | Denial of Service (서비스 거부) | 플러딩, 자원 고갈 |
| **E** | Elevation of Privilege (권한 상승) | 권한 우회, path traversal |

## 페르소나

`security-reviewer` — STRIDE 카테고리별 가정 도전자. weasel words("HTTPS 쓰니까 안전") 차단.

bmad-lite의 `pm-strict`와 비슷한 차단 권한:
- 카테고리별 위협 0건 + N/A 사유 없음 → block
- critical 자산에 0개 mitigation → block
- 클라이언트 검증만 mitigation으로 제시 → block

## 트리거 시스템

`triggers.yaml`이 "어떤 패턴이 threat model을 자동 요구하는지" 정의.

기본 트리거:
- 키워드: auth*, password, payment, refund, ssn, admin, role, secret 등
- 경로: `**/auth/**`, `**/payment/**`, `**/admin/**`
- 엔드포인트: `POST /login`, `POST /webhook/*`

매치되는 스토리/파일에 threat model 없으면 게이트가 경고.

## State Machine

```
[draft] → [reviewed] → [approved] → [applied]
            ↓             ↓
         [draft]      [reviewed]    (롤백 허용)
```

| 상태 | 의미 |
|-----|-----|
| draft | 분석 중. STRIDE 항목 채우는 중 |
| reviewed | 6 카테고리 모두 위협 또는 N/A 사유 있음 |
| approved | 이해관계자 승인. 구현 가능 |
| applied | 모든 mitigation 'implemented' 또는 'deferred' |

## 추가되는 게이트

| 게이트 | severity | 역할 |
|-------|---------|------|
| `check-threat-coverage.sh` | warning | sensitive 파일·스토리에 모델 미연결 시 경고 |

## 산출물

```
.harness/threat-model-lite/
├── models/
│   └── tm-2026-04-30-password-reset.yaml
├── triggers.yaml                    # 트리거 키워드/경로 (프로젝트 로컬)
└── (state)
```

## 시나리오 예시

**비밀번호 재설정 기능 — bmad-lite 스토리 위에 STRIDE 적용**

```bash
# 0. 가정: bmad-lite로 스토리 st-2026-04-30-password-reset 이미 있음
#    narrative에 "password" 포함 → 게이트가 threat model 요구 경고

# 1. 모델 생성
/threat new password-reset \
  --target-kind story \
  --target-ref st-2026-04-30-password-reset \
  --description "Password reset via email link"

# 2. STRIDE 카테고리별 위협 + mitigation 추가
/threat add tm-2026-04-30-password-reset --category S \
  --threat "Attacker uses leaked email to request reset" \
  --mitigation "Rate limit per email (5/hour)" \
  --mitigation "SMS notification to account on reset" \
  --likelihood medium --impact high

/threat add tm-2026-04-30-password-reset --category T \
  --threat "Reset token modified in transit" \
  --mitigation "Token = HMAC(user_id + expiry + secret)" \
  --likelihood low --impact high

/threat add tm-2026-04-30-password-reset --category I \
  --threat "Reset link logged in server access logs" \
  --mitigation "Strip query string before logging" \
  --mitigation "Token has 1h TTL, single-use" \
  --likelihood high --impact high

/threat add tm-2026-04-30-password-reset --category D \
  --threat "Massive reset requests overwhelm email service" \
  --mitigation "Queue + backpressure on email send" \
  --mitigation "Per-IP rate limit on /password/reset endpoint" \
  --likelihood medium --impact medium

# R, E는 yaml 직접 편집해서 not_applicable_reason 또는 위협 추가

# 3. yaml 직접 편집 — assets, trust_boundaries, R/E 카테고리 처리

# 4. 리뷰 (게이트 통과 필요)
/threat review tm-2026-04-30-password-reset
# → block: "repudiation: missing"
# → yaml 수정: stride.repudiation.not_applicable_reason: "no audit trail required for password reset itself; login audit covers"
# → 재시도 → pass

# 5. 승인 → 구현
/threat approve tm-2026-04-30-password-reset

# 6. 구현 후 mitigation_status 업데이트 → apply
/threat apply tm-2026-04-30-password-reset
```

## 다른 메서드와의 조합

| 조합 | 효과 |
|-----|------|
| `+ bmad-lite` | 스토리 narrative에 sensitive 키워드 → 자동 경고. pm-strict + security-reviewer 협업 |
| `+ ouroboros` | 위협 매트릭스가 시드 AC ("system MUST rate limit") 정당화 |
| `+ exploration` | 특정 공격 가능성 spike → 학습 → 위협으로 등록 |
| `+ incident-review` | 과거 incident가 미래 모델의 evidence (links.related_incidents) |
| `+ parallel-change` | 마이그레이션 도중 mitigation 누락 안 되도록 검증 |
| `+ strangler-fig` | 신규 모듈에 위협 모델, legacy 폐기 시점에 mitigation 인계 확인 |

## 안티패턴

- ❌ **6 카테고리 모두 N/A** — 그건 분석 안 한 것. 최소 1개는 위협 등록
- ❌ **HTTPS 쓰니까 안전** — security-reviewer가 차단. cert pinning, HSTS, 회전 등 구체화 필요
- ❌ **클라이언트 검증만 mitigation** — 항상 server-side 짝 필요
- ❌ **likelihood: low** 일괄 적용 — likelihood는 관찰값이지 선택값 아님
- ❌ **모델 없이 코드 작성 → 사후 모델** — 정의상 의미 없음. 설계 단계 필수

## 한계 (v0.1)

- DREAD 점수 미지원 (likelihood/impact만)
- 트리거 매치는 키워드 substring/glob — 정규식·LLM 의미 매칭 미지원
- mitigation 효과성 자동 검증 없음 (사람이 판단)
- 자동 OWASP Top 10 매핑 없음 (수동 `compliance.frameworks`)

## 진화 계획

| 버전 | 추가 |
|-----|------|
| v0.1 (현재) | STRIDE-lite, 트리거, 4-state, security-reviewer 페르소나 |
| v0.2 | DREAD 점수 옵션, OWASP Top 10 자동 매핑 |
| v0.3 | LLM 기반 위협 발견 (코드 + 스토리 분석), threat library |
