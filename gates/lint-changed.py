#!/usr/bin/env python3
"""변경한 줄에서 발생한 eslint 오류(severity 2)만 검사한다.

기존 파일에 남아 있는 오류(baseline)는 건드리지 않고, 새로 쓰거나 고친 줄은 오류 0을 요구한다.
(손대는 파일 위주로 정리하고, 범위 밖 대규모 리팩터링은 강요하지 않는다)

사용:
  lint-changed.py --staged            # git 스테이징된 변경
  lint-changed.py --worktree [files]  # 작업 트리 변경 (files 생략 시 전체 변경 파일)
종료코드: 0 통과, 1 오류 있음, 2 사용법/환경 오류
"""
import json, re, subprocess, sys

# 제외 경로: 환경변수 LINT_CHANGED_EXCLUDE(정규식)로 덮어쓸 수 있다.
EXCLUDE = re.compile(os.environ.get('LINT_CHANGED_EXCLUDE', r'^(supabase/|node_modules/|\.next/|.*\.d\.ts$|.*database\.types\.ts$)'))
EXT = ('.ts', '.tsx')

REPO_ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()

def run(cmd, check=False):
    return subprocess.run(cmd, capture_output=True, text=True)

def changed_files(staged, explicit):
    if explicit:
        return [f for f in explicit if f.endswith(EXT) and not EXCLUDE.match(f)]
    if staged:
        out = run(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR']).stdout.split()
    else:
        out = run(['git', 'diff', '--name-only', '--diff-filter=ACMR', 'HEAD']).stdout.split()
        out += run(['git', 'ls-files', '--others', '--exclude-standard']).stdout.split()
    return sorted({f for f in out if f.endswith(EXT) and not EXCLUDE.match(f)})

def changed_ranges(path, staged):
    tracked = run(['git', 'ls-files', '--error-unmatch', path]).returncode == 0
    if not tracked and not staged:
        return None  # 신규(untracked) 파일: 전체 줄
    cmd = ['git', 'diff', '-U0'] + (['--cached'] if staged else ['HEAD']) + ['--', path]
    diff = run(cmd).stdout
    if staged and not diff:
        return None
    ranges = []
    for m in re.finditer(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', diff, re.M):
        start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        if count:
            ranges.append((start, start + count - 1))
    # 신규 추가 파일(스테이징) 여부: HEAD에 없으면 전체 줄
    if staged and run(['git', 'cat-file', '-e', f'HEAD:{path}']).returncode != 0:
        return None
    return ranges

def main():
    args = sys.argv[1:]
    staged = '--staged' in args
    explicit = [a for a in args if not a.startswith('--')]
    files = changed_files(staged, explicit)
    if not files:
        return 0
    res = run(['npx', '--no-install', 'eslint', '-f', 'json', *files])
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        sys.stderr.write('eslint 실행 실패:\n' + (res.stderr or res.stdout)[:500] + '\n')
        return 2
    problems = []
    for r in data:
        rel = os.path.relpath(r['filePath'], REPO_ROOT)
        ranges = changed_ranges(rel, staged)
        for m in r['messages']:
            if m.get('severity') != 2:
                continue
            line = m.get('line', 0)
            if ranges is None or any(a <= line <= b for a, b in ranges):
                problems.append(f"{rel}:{line}  {m['message']}  ({m.get('ruleId')})")
    if problems:
        sys.stderr.write('변경한 줄에 lint 오류가 있습니다 (기존 줄의 오류는 제외):\n')
        for p in problems[:25]:
            sys.stderr.write('  ' + p + '\n')
        if len(problems) > 25:
            sys.stderr.write(f'  ... 외 {len(problems) - 25}건\n')
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
