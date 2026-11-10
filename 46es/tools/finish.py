"""Finish a 46es change before committing: staged scope, static checks, whitespace, author identity, report.

Run from any directory after staging (git add <files>): python -B 46es/tools/finish.py
  1. staged files: listed by area; unstaged or untracked 46es files are reported (they are not checked)
  2. check_repository.py (checks the index as the intended commit) and smoke_test.py
  3. git diff --cached --check
  4. git config user.email must be the repository-local zzskm noreply address (never the global identity)
  5. prints the five-line report template (AGENTS.md §10)
Exits non-zero at the first failing step.

--hook is the git pre-commit mode (.githooks/pre-commit, enabled once per clone with
git config core.hooksPath .githooks): steps 1-4 without smoke_test.py (CI runs it) and without the report.
"""
import argparse
import subprocess
import sys
from pathlib import Path

from common import ROOT

REPO = ROOT.parent
EMAIL = '11306842+zzskm@users.noreply.github.com'
# Paths outside 46es/ that a 46es change may touch together with it.
SHARED = ('CLAUDE.md', '.github/workflows/46es-check.yml', '.gitattributes', '.githooks/pre-commit')


def git(*args, check=True):
    result = subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, text=True, encoding='utf-8')
    if check and result.returncode:
        sys.exit(f'git {" ".join(args)} failed:\n{result.stderr}')
    return result


def lines(text):
    return [line for line in text.splitlines() if line]


def step(title):
    print(f'\n== {title}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--hook', action='store_true', help='pre-commit mode: no smoke test, no report')
    hook = parser.parse_args().hook

    step('staged scope')
    staged = lines(git('diff', '--cached', '--name-status').stdout)
    if not staged:
        sys.exit('nothing staged: git add the files of this change first')
    outside = [row for row in staged if not row.split('\t')[-1].startswith('46es/') and row.split('\t')[-1] not in SHARED]
    for row in staged:
        print('  ' + row)
    if outside:
        sys.exit(f'staged files outside 46es/ and {SHARED}: commit them separately\n  ' + '\n  '.join(outside))
    unstaged = lines(git('diff', '--name-only', '--', '46es').stdout)
    untracked = lines(git('ls-files', '--others', '--exclude-standard', '--', '46es').stdout)
    if unstaged or untracked:
        print('  not staged (not part of this check):')
        for path in unstaged:
            print('    modified  ' + path)
        for path in untracked:
            print('    untracked ' + path)

    for script in ('check_repository.py',) if hook else ('check_repository.py', 'smoke_test.py'):
        step(script)
        if subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / script)]).returncode:
            sys.exit(f'{script} failed')

    step('git diff --cached --check')
    whitespace = git('diff', '--cached', '--check', check=False)
    if whitespace.returncode:
        sys.exit(whitespace.stdout or whitespace.stderr)
    print('  OK')

    step('author')
    email = git('config', 'user.email', check=False).stdout.strip()
    local = git('config', '--local', 'user.email', check=False).stdout.strip()
    if email != EMAIL or local != EMAIL:
        sys.exit(f'git user.email is {email!r} (local {local!r}); set the repository-local identity:\n'
                 f'  git config user.name zzskm\n  git config user.email {EMAIL}')
    print(f'  {git("config", "user.name").stdout.strip()} <{email}>')
    if hook:
        return

    step('report (AGENTS.md §10)')
    print('변경: 무엇을 해결했고 어떤 파일이 현행인가.\n'
          '검증: 실제 실행한 검사와 결과. (정적 검사·스모크 통과, 위 출력)\n'
          '남은 항목: 미실행 검사 또는 실물 확인.\n'
          '반영: 로컬 커밋 / 원격 브랜치 / PR / main / 게시 상태.\n'
          '다음 행동: 다음 작업자가 바로 수행할 한 가지.')


if __name__ == '__main__':
    main()
