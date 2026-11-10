"""Shared helpers for the 46es tools: repository root, SolidCraft CLI path, hashes, input fingerprints and LF JSON.

Importing this module also switches stdout/stderr to UTF-8, so Korean output works in a cp949 console
without PYTHONUTF8=1. Read and write text files with an explicit encoding.
"""
import ast
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# SOLIDCRAFT_CLI overrides the default install path (other drive, CI runner, side-by-side versions).
CLI = Path(os.environ.get('SOLIDCRAFT_CLI') or 'C:/Program Files/SolidCraft/solidcraft-cli.exe')

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure') and (_stream.encoding or '').lower().replace('-', '') != 'utf8':
        _stream.reconfigure(encoding='utf-8')


def sha(path):
    """SHA-256 of the file bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_ast(node):
    """ast.dump without None/empty fields, so the text is the same on Python 3.12 and 3.13+."""
    if isinstance(node, ast.AST):
        fields = [f'{k}={_canonical_ast(v)}' for k in node._fields
                  if (v := getattr(node, k, None)) is not None and v != []]
        return f"{type(node).__name__}({','.join(fields)})"
    if isinstance(node, list):
        return '[' + ','.join(map(_canonical_ast, node)) + ']'
    return repr(node)


def fingerprint(path):
    """SHA-256 of the file, or of its syntax tree for Python sources (comment-only edits keep the fingerprint).
    Records that name their inputs ({path relative to 46es: fingerprint}) are compared with this."""
    path = Path(path)
    if path.suffix == '.py':
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        return 'ast:' + hashlib.sha256(_canonical_ast(tree).encode('utf-8')).hexdigest()
    return sha(path)


def fingerprints(rels):
    """{rel: fingerprint} for paths relative to the 46es root, in the given order."""
    return {rel: fingerprint(ROOT / rel) for rel in rels}


def changed_inputs(recorded):
    """Paths whose recorded fingerprint differs from the working tree (missing files count as changed)."""
    return [rel for rel, digest in recorded.items()
            if not (ROOT / rel).is_file() or fingerprint(ROOT / rel) != digest]


def json_text(data, indent=1, sort_keys=False):
    """JSON as written to tracked files: UTF-8 text, final newline. Without sort_keys the key order is the
    insertion order, so a script that builds its dicts deterministically (sorted sets, fixed lists) writes the
    same bytes each run while keeping the readable field order of its records."""
    return json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=sort_keys) + '\n'


def write_json(path, data, indent=1, sort_keys=False):
    """Write JSON with LF line endings on every platform (CRLF would change the hash of a tracked file)."""
    Path(path).write_text(json_text(data, indent, sort_keys), encoding='utf-8', newline='\n')


def write_text(path, text):
    """Write UTF-8 text with LF line endings."""
    Path(path).write_text(text, encoding='utf-8', newline='\n')
