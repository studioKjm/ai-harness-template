---
description: Generate layer-aware technical design document from seed spec. USE AFTER /seed and BEFORE /decompose. Maps features to 3-tier architecture, surfaces discussion points before final design.
---

# /trd — Technical Requirements Document (기술 설계서)

> 3-tier layered architecture 기반 기술 설계서를 작성합니다.
> **바로 설계서를 작성하지 않습니다.** 먼저 큰 그림을 소개하고, 논의점을 제시합니다.

---

## 워크플로우

### Phase 1: 탐색 (Explore)

1. **프로젝트 현황 파악**
   - 관련 문서 확인: `docs/`, `ARCHITECTURE_INVARIANTS.md`, seed spec (`.ouroboros/seeds/`)
   - 현재 코드베이스 구조와 상태를 파악합니다
   - 기존 레이어 분리 상태를 점검합니다

2. **요구사항 확인**
   - seed spec이 있다면 `goal`, `constraints`, `acceptance_criteria` 기반으로 진행
   - 없다면 사용자에게 기능 설명을 요청합니다

### Phase 2: 큰 그림 제시

3-tier layered architecture를 반드시 준수하며, 큰 그림을 사용자에게 먼저 소개합니다:

```
[Presentation Layer]  ──→  [Logic Layer]  ──→  [Data Layer]
   UI/HTTP 경계              비즈니스 규칙          저장/불러오기
```

각 레이어별로 설명합니다:
- **Presentation**: 어떤 엔드포인트/페이지/컴포넌트가 필요한가?
- **Logic**: 어떤 비즈니스 규칙을 처리해야 하는가?
- **Data**: 어떤 데이터를 저장/조회/외부 연동해야 하는가?
- 그 밖에 필요한 레이어(e.g., Infrastructure, Shared)가 있다면 최소한으로 추가합니다

### Phase 3: 논의점 제시

**바로 구현으로 넘어가지 않습니다.** 다음을 사용자에게 제시합니다:

1. **기술적으로 모호한 부분**
   - 레이어 간 통신 방식 (DTO vs Interface vs Plain Object)
   - 외부 서비스 연동 위치 (Logic vs Data)
   - 에러 핸들링 전략 (어느 레이어에서 잡을 것인가)

2. **중요 결정 사항**
   - 각 결정에 대해 **resource 소모**(개발 시간, 복잡도)와 **impact**(유지보수, 확장성)를 설명
   - 기술 배경이 깊지 않은 사람도 이해할 수 있게 쉽게 설명

3. **레이어 분리 전략**
   - 디렉토리 구조 제안
   - 각 모듈이 어느 레이어에 속하는지 명시
   - 레이어 간 의존성 방향 확인

### Phase 4: 최종 설계서 작성

모든 논의가 완료된 후, `/docs/TRD.md`를 작성합니다.

#### TRD 구조

```markdown
# Technical Requirements Document — [Feature Name]

## 1. Overview
- 목표 요약
- 아키텍처 패턴: 3-tier layered

## 2. Layer Design

### 2.1 Presentation Layer
- 엔드포인트/페이지 목록
- 요청/응답 형식 (DTO)
- 입력 검증 규칙

### 2.2 Logic Layer
- 서비스 모듈 목록
- 비즈니스 규칙 상세
- 트랜잭션 경계

### 2.3 Data Layer
- 엔티티/테이블 설계
- 레포지토리 인터페이스
- 외부 연동 목록

## 3. Layer Communication
- Presentation → Logic: [방식]
- Logic → Data: [방식]
- 데이터 전달 형식: [DTO/Interface]

## 4. Directory Structure
- 파일/디렉토리 배치 계획

## 5. Test Strategy
- Logic Layer: 단위 테스트 (순수 비즈니스 로직)
- Data Layer: 통합 테스트
- Presentation Layer: E2E / API 테스트
- 구현과 테스트 함께 작성

## 6. Decisions & Trade-offs
- 주요 결정 사항과 근거

## 7. Implementation Order
- 레이어별 구현 순서 (보통 Data → Logic → Presentation)
- 각 단계별 테스트 작성 시점
```

### Phase 5: 테스트 설계

TRD 작성 후, 필요한 모듈들에 대한 테스트를 설계합니다:

- **해당 모듈의 책임만 정확히 테스트** — 다른 레이어의 책임을 테스트하지 않음
- **mock은 레이어 경계에서만 사용** — 접착제 코드를 mock으로 테스트하지 않음
- **순수 로직에 집중** — 구현을 두 번 쓰는 것이 아니라 동작을 검증
- **구현 직후 바로 해당 테스트 작성** — 일괄 작성 금지

---

## 핵심 원칙

1. **논의 먼저, 설계서 나중** — 바로 문서를 작성하지 않고 논의점을 먼저 제시
2. **3-tier 필수 준수** — Presentation / Logic / Data 레이어 분리
3. **레이어 스킵 금지** — Presentation → Logic → Data 순서로만 호출
4. **테스트 함께 작성** — 구현과 테스트는 한 쌍
5. **쉬운 설명** — resource 소모와 impact 위주로 설명

---

## Output

- `/docs/TRD.md` (최종 설계서)
- seed spec 업데이트: `architecture` 섹션 채우기
- 테스트 계획 포함
