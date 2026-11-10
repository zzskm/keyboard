"""One cache for SolidCraft CLI evaluations, keyed by the exact CAD bytes (plan 3-7).

46es/.cache/eval/<first 16 hex of the file's SHA-256>.json holds `solidcraft-cli eval` of that file. A changed
file has another key, so a stale evaluation is never read (the old mtime/existence checks could, depending on
checkout order). build_seam_v5.py seeds the entry of the model it has just saved and measured, so later stages
read it instead of evaluating the same bytes again. python 46es/tools/pipeline.py --clean removes entries whose
file is no longer in the tree.
"""
import json
import subprocess
from pathlib import Path

from common import ROOT, CLI, sha

EVAL_CACHE = ROOT / '.cache/eval'


def cache_path(digest):
    return EVAL_CACHE / f'{digest[:16]}.json'


def evaluation(source, cli=CLI):
    """The CLI measurement of `source` and the cache file holding it."""
    cached = cache_path(sha(source))
    if not cached.exists():
        EVAL_CACHE.mkdir(parents=True, exist_ok=True)
        pending = cached.with_suffix('.tmp.json')
        subprocess.run([str(cli), 'eval', '--in', str(source), '--json-out', str(pending)], check=True, capture_output=True)
        pending.replace(cached)
    return json.loads(cached.read_text(encoding='utf-8')), cached


def seed(source, report):
    """Store a measurement taken while `source` was saved (same model, same bytes) under its key."""
    EVAL_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path(sha(source)).write_bytes(Path(report).read_bytes())
