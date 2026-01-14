#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verify demo_data integrity against demo_manifest.csv.

Usage (from repo root):
  python reference_impl_demo\scripts\verify_demo_manifest.py --root reference_impl_demo\demo_data

The manifest is expected at: <root>/demo_manifest.csv
"""

from __future__ import annotations
from pathlib import Path
import argparse, csv, hashlib, sys

def sha256_file(p: Path, buf: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest().lower()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="demo_data folder (contains demo_manifest.csv)")
    args = ap.parse_args()

    root = Path(args.root)
    mf = root / "demo_manifest.csv"
    if not mf.exists():
        print(f"ERROR: missing manifest: {mf}", file=sys.stderr)
        return 2

    missing = []
    mismatch = []
    rows = 0

    with mf.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows += 1
            rel = row["relative_path"]
            exp = row["sha256"].lower()
            p = root / rel
            if not p.exists():
                missing.append(rel)
                continue
            got = sha256_file(p)
            if got != exp:
                mismatch.append((rel, exp, got))

    print(f"rows={rows}")
    print(f"missing={len(missing)}")
    print(f"mismatch={len(mismatch)}")
    if missing:
        print("first few missing:", missing[:5])
    if mismatch:
        print("first few mismatch:", mismatch[:3])

    return 0 if (not missing and not mismatch) else 1

if __name__ == "__main__":
    raise SystemExit(main())
