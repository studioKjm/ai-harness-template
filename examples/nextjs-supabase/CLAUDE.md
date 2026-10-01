# CLAUDE.md — Next.js + Supabase 예시

`init.sh`가 `supabase`를 감지하면 skills, 훅, 게이트가 자동 설치된다. 이 파일은 그 위에 프로젝트에서 직접 적을 규칙의 예시다. **짧게 유지**하고, 코드를 읽으면 알 수 있는 내용은 쓰지 않는다.

@AGENTS.md

## 반드시 지킬 것
- 원격(운영/스테이징) Supabase에는 쓰지 않는다. 로컬 `supabase start`로 개발·검증한다. 원격 적용은 사람이 직접 한다.
- 기존 마이그레이션은 수정하지 않는다. 새 마이그레이션을 추가한다 (`supabase-migration` skill).
- 새 테이블은 같은 마이그레이션에서 RLS와 역할별 정책을 만든다. `using (true)` 금지.
- 권한 판단을 화면에만 두지 않는다. RLS가 최종 방어선이다.

## 명령
- 로컬 DB: `supabase start|stop`, `supabase db reset --local`, `supabase db advisors --local`
- 타입: `supabase gen types typescript --local > <경로>`
- 개발 서버 / 린트 / 타입체크: 프로젝트 `package.json` 스크립트

## 작업 방식
- 완료 선언 전에 `verify` skill로 시드 계정 E2E 증거를 남긴다.
- 마이그레이션·권한 변경 후에는 `rls-security-reviewer` 서브에이전트로 별도 컨텍스트 리뷰를 받는다.
- 기존 오류가 많은 코드베이스는 `gates/lint-changed.py`로 "변경한 줄만" 검사한다.

## Next.js 주의
- Next.js 16.3 이상은 `next dev`가 `AGENTS.md`/`CLAUDE.md`의 `BEGIN:nextjs-agent-rules` 블록을 자동 관리한다. 그 블록은 수정하지 말고, 프로젝트 규칙은 블록 바깥에 쓴다.
