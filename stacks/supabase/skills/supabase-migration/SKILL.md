---
name: supabase-migration
description: DB 스키마를 바꾸거나 테이블/컬럼/RLS 정책/함수를 추가할 때 사용. 마이그레이션 생성, RLS 체크리스트, 로컬 검증, 타입 재생성 절차를 따른다. "테이블 추가", "컬럼 추가", "RLS", "마이그레이션" 요청에 사용.
---

# Supabase 마이그레이션 절차

원격(운영/스테이징) DB에는 쓰지 않는다. 모든 검증은 로컬 Supabase에서 한다. 원격 적용은 사용자가 직접, 합의된 절차로 한다.

1. 로컬 Supabase 실행 확인: `supabase status` (꺼져 있으면 `supabase start`)
2. `supabase migration new <snake_case_name>` 으로 **새 파일**을 만든다. `supabase/migrations/`의 기존 파일은 수정·삭제·이름 변경하지 않는다 (`check-migrations.sh` 게이트가 막는다).
3. SQL 작성 규칙
   - 새 테이블은 같은 파일에서 `alter table ... enable row level security;` 와 역할별 정책을 함께 만든다.
   - `using (true)` / `with check (true)` 정책 금지. 정책은 사용자 역할·소유 조직 기준으로 작성한다.
   - 정책에서 `auth.uid()`는 `(select auth.uid())` 형태로 감싼다 (initplan 최적화).
   - `anon`에 불필요한 GRANT를 주지 않는다. SECURITY DEFINER 함수는 `set search_path = ''`.
   - 정책과 조인에 쓰이는 FK 컬럼에는 인덱스를 만든다.
4. 검증: `supabase db reset --local` (시드까지 적용되는지) 후 `supabase db advisors --local --fail-on error`. 이미 존재하던 오류(baseline)와 이번 변경으로 생긴 오류를 구분해서 보고한다.
5. 타입 재생성: `supabase gen types typescript --local > <types 경로>`
6. 새 컬럼/테이블이 개발 시드에 필요하면 `supabase/seed.sql`도 갱신한다.
7. 보고: 변경 요약, advisors 결과, 원격 적용 시 주의점(기존 화면·권한 영향).
