"""Publish the guide to GitHub Pages in one command: build -> browser check -> copy -> commit/push -> confirm live.

  python 46es/guide/publish_guide.py              # run on a clean, pushed commit of origin/main
  python 46es/guide/publish_guide.py --dry-run    # build and check only; no Pages commit

It refuses to publish when 46es/ has uncommitted changes, when HEAD is not on origin/main (--allow-branch
relaxes this to "pushed to some origin branch"), when the Pages clone has local changes, or when the Pages
clone's commit author is not the zzskm noreply address. The build gets a build.json (source commit, review
model hash, SHA-256 of every file); the live check waits until https://zzskm.github.io/<site>/build.json names
this commit and the served index.html matches the build.
Options: --pages DIR (Pages clone)  --site NAME (folder in it, default keyboard-46es)  --keep NAME (folders in the
site the build does not own, default v4)  --skip-browser  --no-wait  --trailer TEXT (commit trailer, repeatable)
"""
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
NOREPLY = '11306842+zzskm@users.noreply.github.com'
PAGES = Path('D:/work/zzskm.github.io')
LIVE = 'https://zzskm.github.io'


def die(message):
    raise SystemExit(f'publish_guide: {message}')


def git(cwd, *args, check=True):
    r = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, encoding='utf-8')
    if check and r.returncode:
        die(f"git {' '.join(args)} failed in {cwd}:\n{r.stderr.strip()}")
    return r.stdout.strip() if check else r


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_state(allow_branch):
    git(REPO, 'fetch', '-q', 'origin')
    if git(REPO, 'status', '--porcelain', '--', '46es'):
        die('46es/ has uncommitted changes; publish only a committed state')
    head = git(REPO, 'rev-parse', 'HEAD')
    on_main = git(REPO, 'merge-base', '--is-ancestor', head, 'origin/main', check=False).returncode == 0
    if not on_main:
        if not allow_branch:
            die(f'HEAD {head[:7]} is not on origin/main (merge first, or pass --allow-branch)')
        if not git(REPO, 'branch', '-r', '--contains', head):
            die(f'HEAD {head[:7]} is not pushed to any origin branch')
    return head, git(REPO, 'rev-parse', '--abbrev-ref', 'HEAD'), on_main


def build(out, cli, head, branch):
    if out.exists():
        shutil.rmtree(out)
    cmd = [sys.executable, '-B', str(HERE / 'build_guide.py'), '--out', str(out), '--clean-img']
    if cli:
        cmd += ['--cli', cli]
    subprocess.run(cmd, check=True)
    data = json.loads((out / 'assembly.json').read_text(encoding='utf-8'))
    files = {p.relative_to(out).as_posix(): sha256(p) for p in sorted(out.rglob('*')) if p.is_file()}
    record = dict(source_repo='zzskm/keyboard', source_commit=head, source_branch=branch,
                  review_model_sha256=data['model_sha'], steps=len(data['steps']),
                  built_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), files=files)
    (out / 'build.json').write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    return record


def browser_check(out):
    import check_browser
    server, url = check_browser.serve(out)
    try:
        return check_browser.run(url, str(HERE / '.cache' / 'publish-'))
    finally:
        server.shutdown()


def sync(out, pages, site, keep, head, model_sha, trailers):
    if git(pages, 'config', 'user.email') != NOREPLY:
        die(f'{pages}: user.email is not {NOREPLY}; refusing to commit with another identity')
    if git(pages, 'status', '--porcelain'):
        die(f'{pages} has local changes; clean it first')
    git(pages, 'pull', '--ff-only', '-q')
    target = pages / site
    target.mkdir(exist_ok=True)
    for child in target.iterdir():
        if child.name in keep:
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(out, target, dirs_exist_ok=True)
    git(pages, 'add', '-A', '--', site)
    if git(pages, 'diff', '--cached', '--quiet', check=False).returncode == 0:
        return git(pages, 'rev-parse', 'HEAD'), False
    message = (f'{site}: 46es 가이드 게시 (keyboard {head[:7]})\n\n'
               f'원본 zzskm/keyboard@{head}, 검토 모델 SHA-256 {model_sha[:12]}. guide/publish_guide.py로 생성·검사.\n')
    if trailers:
        message += '\n' + '\n'.join(trailers) + '\n'
    git(pages, 'commit', '-q', '-m', message)
    for attempt in range(3):
        if git(pages, 'push', '-q', 'origin', 'HEAD:main', check=False).returncode == 0:
            return git(pages, 'rev-parse', 'HEAD'), True
        git(pages, 'pull', '--rebase', '-q')     # the Pages repo receives automatic data commits
    die('push to the Pages repository failed three times')


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'publish-guide', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def wait_live(site, record, timeout):
    base = f'{LIVE}/{site}/'
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            live = json.loads(fetch(f'{base}build.json?t={int(time.time())}'))
            if live.get('source_commit') == record['source_commit']:
                index = hashlib.sha256(fetch(f'{base}index.html?t={int(time.time())}')).hexdigest()
                if index != record['files']['index.html']:
                    die('the live build.json names this commit but index.html differs from the build')
                return base
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            pass
        time.sleep(15)
    die(f'{base} did not serve this build within {timeout} s (Pages may still be deploying)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pages', default=str(PAGES))
    ap.add_argument('--site', default='keyboard-46es')
    ap.add_argument('--keep', nargs='*', default=['v4'])
    ap.add_argument('--cli')
    ap.add_argument('--allow-branch', action='store_true')
    ap.add_argument('--skip-browser', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-wait', action='store_true')
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--trailer', action='append', default=[])
    a = ap.parse_args()

    head, branch, on_main = source_state(a.allow_branch)
    out = HERE / 'out_publish'
    record = build(out, a.cli, head, branch)
    browser = None if a.skip_browser else browser_check(out)
    summary = dict(source_commit=head, source_on_main=on_main, review_model=record['review_model_sha256'][:12],
                   files=len(record['files']), browser=browser or 'skipped')
    if a.dry_run:
        summary['published'] = False
    else:
        pages_commit, changed = sync(out, Path(a.pages), a.site, set(a.keep), head, record['review_model_sha256'], a.trailer)
        summary.update(pages_commit=pages_commit, pages_changed=changed)
        summary['live'] = 'not checked' if a.no_wait else wait_live(a.site, record, a.timeout)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
