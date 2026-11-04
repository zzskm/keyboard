#!/usr/bin/env python3
"""Regenerate or check 46es/manifest.json from the git index.

Every file under 46es/ that is staged (tracked) is listed, except manifest.json
itself. Sizes and hashes come from the staged blobs, i.e. exactly what the next
commit will contain, not from the working-tree files. With core.autocrlf=true
the working tree can hold CRLF copies of LF blobs; hashing those would give
values that match neither git nor a fresh clone.

Usage (from anywhere inside the repository):
    git add <changed files under 46es>
    python -I 46es/tools/update_manifest.py           # rewrite manifest.json
    git add 46es/manifest.json
    python -I 46es/tools/update_manifest.py --check   # exit 1 if stale

Standard library only.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the 46es/ directory
MANIFEST = ROOT / "manifest.json"


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True
    ).stdout


def build_entries() -> list:
    entries = []
    # Paths are printed relative to ROOT because of -C; -z keeps them unquoted.
    for record in git("ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, blob_sha, stage = meta.decode().split()
        path = path.decode("utf-8")
        if stage != "0":
            raise SystemExit(f"unmerged path in index: {path}")
        if path == MANIFEST.name or mode == "160000":  # self, submodules
            continue
        body = git("cat-file", "blob", blob_sha)
        entries.append({
            "path": path,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "git_blob_sha": blob_sha,
        })
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="only compare; exit 1 if manifest.json is stale")
    args = parser.parse_args()

    current = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    manifest = dict(current)
    manifest["files"] = build_entries()

    if args.check:
        old = {e["path"]: e for e in current.get("files", [])}
        new = {e["path"]: e for e in manifest["files"]}
        stale = sorted(p for p in old.keys() | new.keys() if old.get(p) != new.get(p))
        for p in stale:
            state = "missing" if p not in old else "removed" if p not in new else "changed"
            print(f"{state}: {p}")
        print("manifest.json is stale" if stale else f"manifest.json OK ({len(new)} files)")
        return 1 if stale else 0

    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    MANIFEST.write_bytes(text.encode("utf-8"))  # LF, no BOM
    print(f"wrote {MANIFEST.name}: {len(manifest['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
