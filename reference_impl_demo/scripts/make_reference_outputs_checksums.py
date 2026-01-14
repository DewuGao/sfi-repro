from pathlib import Path
import hashlib

OUT = Path('reference_outputs')
FILES = [
    'DIST_demo_long.csv',
    'runlog_demo.json',
    'RUN_NOTES.txt',
    'RUN_EXITCODE.txt',
    'RUN_STDERR.txt',
    'RUN_STDOUT.txt',
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest().lower()

lines = []
missing = []
for name in FILES:
    fp = OUT / name
    if not fp.exists():
        missing.append(name)
        continue
    lines.append(f'{sha256(fp)}  reference_outputs/{name}')

out = OUT / 'checksums_sha256_reference_outputs.txt'
out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Wrote:', out.resolve())
if missing:
    print('WARNING: missing files (not included in checksums):', missing)

