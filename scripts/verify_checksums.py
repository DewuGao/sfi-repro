"""Verify SHA256 checksums for files in a release package.

Usage:
  python scripts/verify_checksums.py --root . --checksums checksums_sha256.txt

Notes:
  - By default, this script ignores the checksum file itself.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_checksums(txt: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        digest = parts[0]
        relpath = ' '.join(parts[1:]).strip()
        items.append((digest, relpath))
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=str, default='.', help='Release root directory')
    ap.add_argument('--checksums', type=str, default='checksums_sha256.txt', help='Checksum file (relative to root)')
    ap.add_argument('--strict', action='store_true', help='Fail if any listed file is missing')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    chk_path = (root / args.checksums).resolve()

    if not chk_path.exists():
        raise FileNotFoundError(f'Checksum file not found: {chk_path}')

    entries = parse_checksums(chk_path.read_text(encoding='utf-8'))
    if not entries:
        raise ValueError('No checksum entries found.')

    ok = 0
    missing = 0
    mismatch = 0

    for expected, rel in entries:
        # Ignore the checksum file itself by default.
        if Path(rel).as_posix() == Path(args.checksums).as_posix():
            continue

        p = root / rel
        if not p.exists():
            missing += 1
            print(f'MISSING  {rel}')
            continue
        got = sha256_file(p)
        if got.lower() != expected.lower():
            mismatch += 1
            print(f'BAD      {rel}')
            print(f'  expected: {expected}')
            print(f'  got:      {got}')
        else:
            ok += 1
            print(f'OK       {rel}')

    print('---')
    print(f'OK: {ok}, MISSING: {missing}, MISMATCH: {mismatch}')

    if mismatch > 0:
        return 2
    if missing > 0 and args.strict:
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
