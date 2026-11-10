"""Cache SolidCraft CLI evaluations by the exact source CAD bytes."""
import json
import subprocess
from pathlib import Path

from common import CLI, sha


def evaluation(source, cache_dir, cli=CLI):
    source = Path(source)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = sha(source)
    cached = cache_dir / f'eval_{source.stem}_{digest[:16]}.json'
    if not cached.exists():
        subprocess.run([str(cli), 'eval', '--in', str(source), '--json-out', str(cached)],
                       check=True, capture_output=True)
    data = json.loads(cached.read_text(encoding='utf-8'))
    return data, cached
