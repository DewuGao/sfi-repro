"""End-to-end verification for the SFI reproducibility release.

This script:
  1) Verifies SHA256 checksums (excluding the checksum file itself).
  2) Runs reproduce_key_numbers.py and reproduce_tables.py.
  3) Checks that expected outputs are created and non-empty.

Usage:
  python scripts/verify_release.py --root .
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


def run(cmd: list[str]) -> None:
    print('Running:', ' '.join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)
    if res.returncode != 0:
        raise RuntimeError(f'Command failed with code {res.returncode}: {cmd}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=str, default='.', help='Release root directory')
    args = ap.parse_args()

    root = Path(args.root).resolve()

    # 1) checksums
    run([sys.executable, str(root / 'scripts' / 'verify_checksums.py'), '--root', str(root)])

    # 2) reproduce outputs
    repro_dir = root / 'repro_outputs'
    tables_dir = repro_dir / 'tables'
    repro_dir.mkdir(exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    run([sys.executable, str(root / 'scripts' / 'reproduce_key_numbers.py'), '--root', str(root), '--out', str(repro_dir)])
    run([sys.executable, str(root / 'scripts' / 'reproduce_tables.py'), '--root', str(root), '--out', str(tables_dir)])

    # 3) sanity checks
    key_path = repro_dir / 'key_numbers.csv'
    if not key_path.exists() or key_path.stat().st_size == 0:
        raise FileNotFoundError('Missing or empty key_numbers.csv')

    key = pd.read_csv(key_path)
    if set(key.columns) != {'key', 'value'}:
        raise ValueError('Unexpected columns in key_numbers.csv')

    expected_keys = {
        'n_images', 'n_metrics', 'n_dimensions', 'power_mean_p',
        'mfs_mean', 'mfs_median', 'dimfs_absdiff_mean', 'dimfs_absdiff_max',
        'direction_p_closer_CN_overall'
    }
    if not expected_keys.issubset(set(key['key'].astype(str))):
        raise ValueError('Missing expected keys in key_numbers.csv')

    csvs = sorted(tables_dir.glob('*.csv'))
    if len(csvs) < 5:
        raise ValueError('Too few table CSVs produced.')
    for p in csvs:
        if p.stat().st_size == 0:
            raise ValueError(f'Empty output table: {p.name}')

    print('---')
    print('Verification PASSED.')
    print(f'Key numbers: {key_path}')
    print(f'Tables: {tables_dir} ({len(csvs)} files)')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
