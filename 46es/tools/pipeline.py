"""One entry point for the 46es generation chain: see which stages are stale and run them in order (plan 2-1, 2-2).

Run from any directory:
  python 46es/tools/pipeline.py              same as --status
  python 46es/tools/pipeline.py --status     each stage: ok / stale (with the reason) / pending after an earlier stage
  python 46es/tools/pipeline.py --run        run the stale stages in order, re-checking each before it runs
  python 46es/tools/pipeline.py --run --from verify_seam      run that stage and every later one
  python 46es/tools/pipeline.py --run --only order1 order2    run just these (in chain order)

Stages (validation.md 「재생성」 lists the same commands):
  seam            tools/build_seam_v5.py                 model/seam_v5_build.json vs the generator inputs and CAD
  order2          tools/export_print_v5.py               order-2 record vs its source CAD and STL/STEP files
  order1          tools/export_print_v5.py --trial       order-1 record vs its three source CADs and files
  verify_seam     inspection/scripts/verify_seam_v5.py   inputs recorded in seam-v5-verification.json
  assembly        tools/build_assembly_reference_v5.py   model/assembly_reference_v5.json hashes
  verify_assembly inspection/scripts/verify_assembly_reference_v5.py   inputs recorded in its verification JSON
  review          guide/review_guide.py                  captures for the current review model and guide spec
                                                         (guide/.cache/visual-review); the verdict stays manual

Staleness is read from the committed records, so --status needs no SolidCraft. Exporter code is not fingerprinted:
after editing export_print_v5.py (or the STL scripts it calls) run --only order1 order2. Every stage run appends
{stage, started, seconds, ok} to 46es/.cache/pipeline-timings.json; --status shows the last successful time.
Publishing the guide stays a separate step after the merge (guide/publish_guide.py).

  python 46es/tools/pipeline.py --clean      delete cache entries nothing current uses (plan 3-7): evaluations of
      files no longer in the tree, the old guide/.cache/v5 build folder and eval files, guide renders other than the
      newest per render id, visual-review runs other than the newest three
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

from common import ROOT, sha, changed_inputs, write_json

REPO = ROOT.parent
DATA = ROOT / 'inspection/data'
TIMINGS = ROOT / '.cache/pipeline-timings.json'
REVIEW_RUNS = ROOT / 'guide/.cache/visual-review'
REVIEW_STEPS = ('standoff', 'trial', 'module')      # AGENTS.md §10; --review-steps changes them
REVIEW_VIEWS = ('reset', 'iso')


def seam_stale():
    from build_seam_v5 import stale_reasons
    return stale_reasons()


def print_stale(trial):
    from export_print_v5 import PARTS, TRIAL_PARTS, source_of
    parts, order = (TRIAL_PARTS, 'order1') if trial else (PARTS, 'order2')
    record = DATA / ('seam-v5-trial-print-set.json' if trial else 'seam-v5-print-set.json')
    if not record.is_file():
        return [f'missing {record.name}']
    rows = {r['file']: r for r in json.loads(record.read_text(encoding='utf-8'))}
    expected = {'46es_v5_' + name: spec for name, spec in parts.items()}
    reasons = [] if set(rows) == set(expected) else ['part list differs from export_print_v5.py']
    sources = {}
    folder = ROOT / 'model/print_v5' / order
    for name, row in rows.items():
        if name not in expected:
            continue
        body, material, flip = expected[name]
        if (row['body'], row['material'], row['print_flip_about_X']) != (body, material, flip):
            reasons.append(f'{name}: body/material/orientation differs from export_print_v5.py')
        source = source_of(body)
        if row['source_sha256'] != sources.setdefault(source, sha(source)):
            reasons.append(f'{source.name} changed since the export')
        for ext, key in (('.stl', 'stl_sha256'), ('.step', 'step_sha256')):
            path = folder / (name + ext)
            if not path.is_file() or sha(path) != row[key]:
                reasons.append(f'{name}{ext} differs from {record.name}')
    return list(dict.fromkeys(reasons))


def record_stale(rel):
    path = ROOT / rel
    if not path.is_file():
        return [f'missing {path.name}']
    inputs = json.loads(path.read_text(encoding='utf-8')).get('inputs')
    if not inputs:
        return [f'{path.name} has no input fingerprints']
    return [f'changed since the run: {name}' for name in changed_inputs(inputs)]


def assembly_stale():
    from build_assembly_reference_v5 import SOURCE, OUTPUT, MANIFEST, MEASUREMENTS, TRIALS_OUTPUT
    if not MANIFEST.is_file():
        return [f'missing {MANIFEST.name}']
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    inputs = {'source_sha': SOURCE, 'trials_sha': TRIALS_OUTPUT, 'measurement_sha': MEASUREMENTS,
              'generator_sha': ROOT / manifest['generator'], 'output_sha': OUTPUT}
    return [f'{path.relative_to(ROOT).as_posix()} differs from {MANIFEST.name} ({key})'
            for key, path in inputs.items() if not path.is_file() or sha(path) != manifest.get(key)]


def review_stale():
    guide = ROOT / 'guide'
    spec = json.loads((guide / 'guide_v5.json').read_text(encoding='utf-8'))
    current = dict(model=sha(guide / spec['model']),
                   spec={name: sha(guide / name) for name in ('guide_v5.json', spec['interactive'])})
    for report in sorted(REVIEW_RUNS.glob('*/review.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(report.read_text(encoding='utf-8'))
        if data.get('review_model_sha256') == current['model'] and data.get('spec_sha256') == current['spec']:
            return []
    return ['no visual-review captures for the current review model and guide spec']


def py(*args):
    return [sys.executable, *args]


STAGES = {
    'seam': (seam_stale, lambda a: py('46es/tools/build_seam_v5.py')),
    'order2': (lambda: print_stale(False), lambda a: py('46es/tools/export_print_v5.py')),
    'order1': (lambda: print_stale(True), lambda a: py('46es/tools/export_print_v5.py', '--trial')),
    'verify_seam': (lambda: record_stale('inspection/data/seam-v5-verification.json'),
                    lambda a: py('-B', '46es/inspection/scripts/verify_seam_v5.py')),
    'assembly': (assembly_stale, lambda a: py('46es/tools/build_assembly_reference_v5.py')),
    'verify_assembly': (lambda: record_stale('inspection/data/assembly-reference-v5-verification.json'),
                        lambda a: py('-B', '46es/inspection/scripts/verify_assembly_reference_v5.py')),
    'review': (review_stale, lambda a: py('-B', '46es/guide/review_guide.py', '--steps', *a.review_steps,
                                          '--views', *REVIEW_VIEWS)),
}


# What each stage reads from earlier stages: --status shows a stage as pending while one of these is stale or pending.
NEEDS = {'order2': ('seam',), 'order1': ('seam',), 'verify_seam': ('seam', 'order2', 'order1'),
         'assembly': ('seam',), 'verify_assembly': ('assembly', 'order1'), 'review': ('assembly',)}


def load_timings():
    try:
        return json.loads(TIMINGS.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []


def record_timing(stage, started, seconds, ok):
    timings = load_timings()
    timings.append(dict(stage=stage, started=started, seconds=round(seconds, 1), ok=ok))
    TIMINGS.parent.mkdir(parents=True, exist_ok=True)
    write_json(TIMINGS, timings, indent=None)


def status():
    last = {t['stage']: t['seconds'] for t in load_timings() if t['ok']}
    behind = set()
    for name, (stale, _) in STAGES.items():
        reasons = stale()
        timing = f'{last[name]:6.1f} s' if name in last else '      -'
        waits = [n for n in NEEDS.get(name, ()) if n in behind]
        if reasons:
            print(f'{name:16} stale   {timing}  ' + '; '.join(reasons[:3]) + (f' (+{len(reasons) - 3})' if len(reasons) > 3 else ''))
            if name == 'seam' and all(r.startswith('input changed: tools/') for r in reasons):
                print(f'{"":16}         only generator code changed: if the model must stay the same, run '
                      'python 46es/tools/build_seam_v5.py --refresh-record instead of --run')
        elif waits:
            print(f'{name:16} pending {timing}  reruns after {", ".join(waits)}')
        else:
            print(f'{name:16} ok      {timing}')
        if reasons or waits:
            behind.add(name)
    return sorted(behind)


def run(args):
    names = list(STAGES)
    if args.only:
        selected = [n for n in names if n in args.only]
    elif args.start:
        selected = names[names.index(args.start):]
    else:
        selected = names
    forced = bool(args.only or args.start)
    ran = []
    for name in selected:
        stale, command = STAGES[name]
        reasons = stale()
        if not reasons and not forced:
            print(f'== {name}: ok, skipped', flush=True)
            continue
        cmd = command(args)
        print(f'== {name}: {"; ".join(reasons[:3]) or "forced"}\n   {" ".join(cmd[1:])}', flush=True)
        started = datetime.now(timezone.utc).isoformat(timespec='seconds')
        t0 = time.perf_counter()
        ok = subprocess.run(cmd, cwd=REPO).returncode == 0
        record_timing(name, started, time.perf_counter() - t0, ok)
        if not ok:
            sys.exit(f'{name} failed after {time.perf_counter() - t0:.0f} s; later stages were not run')
        left = stale()
        if left and name != 'review':
            sys.exit(f'{name} ran but is still stale: {"; ".join(left)}')
        ran.append(f'{name} {time.perf_counter() - t0:.0f} s')
    print('ran: ' + (', '.join(ran) or 'nothing (all stages ok)'))
    if 'review' in [r.split()[0] for r in ran]:
        print('Inspect the captures and record the visual verdict in the change report (guide/README.md 시각 검토).')


def size_of(path):
    return path.stat().st_size if path.is_file() else sum(p.stat().st_size for p in path.rglob('*') if p.is_file())


def clean():
    from cad_eval_cache import EVAL_CACHE
    tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '*.sc'], text=True).split()
    keep = {sha(ROOT / rel)[:16] for rel in tracked if (ROOT / rel).is_file()}
    keep |= {sha(p)[:16] for p in (ROOT / '.cache/v5').glob('*.sc')}        # probe and partial builds
    doomed = [p for p in EVAL_CACHE.glob('*.json') if p.name.split('.')[0] not in keep]
    guide = ROOT / 'guide/.cache'
    doomed += [guide / 'v5', *guide.glob('eval-*.json')]                   # before the shared cache (2026-11-10)
    newest = {}
    for png in sorted((guide / 'renders').glob('*.png'), key=lambda p: p.stat().st_mtime):
        rid = png.stem.rsplit('-', 1)[0]
        if rid in newest:
            doomed += [newest[rid], newest[rid].with_suffix('.script.json')]
        newest[rid] = png
    runs = sorted((p for p in REVIEW_RUNS.glob('*') if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    doomed += runs[3:]
    freed = 0
    for path in doomed:
        if path.exists():
            freed += size_of(path)
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    print(f'removed {sum(1 for _ in doomed)} cache entries, {freed / 1e6:.0f} MB')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--status', action='store_true', help='show stale stages (default)')
    mode.add_argument('--run', action='store_true', help='run stale stages in order')
    mode.add_argument('--clean', action='store_true', help='delete cache entries nothing current uses')
    which = parser.add_mutually_exclusive_group()
    which.add_argument('--from', dest='start', choices=list(STAGES), help='with --run: this stage and all later ones')
    which.add_argument('--only', nargs='+', choices=list(STAGES), help='with --run: only these stages')
    parser.add_argument('--review-steps', nargs='+', default=list(REVIEW_STEPS), help='guide steps for the review stage')
    args = parser.parse_args()
    if (args.start or args.only) and not args.run:
        parser.error('--from/--only need --run')
    if args.clean:
        clean()
    elif args.run:
        run(args)
    else:
        status()


if __name__ == '__main__':
    main()
