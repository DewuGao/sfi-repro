# SFI reproducibility release (public) — v1.4.7.1

This release contains **derived, machine-readable outputs** that support the paper’s reported results, together with **minimal scripts** to re-generate the key summary numbers and table-like CSVs from the released derived outputs (CPU-only; no GPU required).

It is designed for **independent verification** of:
- dataset-level counts (e.g., number of evaluation images),
- metric/dimension configuration (8 metrics; 5 dimensions),
- directional summaries (how often *d*\_CN < *d*\_W),
- released tables used in the manuscript / Supplementary Tables.

> Note: Raw façade images are **not** included in this bundle. A rights-cleared demo image set is a separate, optional route.

## Quick start (CPU-only)

From the package root:

```bash
python -m pip install -r requirements.txt
python scripts/reproduce_key_numbers.py --root . --out repro_outputs
python scripts/reproduce_tables.py --root . --out repro_outputs/tables
```

Expected outputs:
- `repro_outputs/key_numbers.csv`
- `repro_outputs/tables/table_*.csv`

## Package contents

- `derived_outputs/distances/`
  - Long-form directional distances to the Chinese (*d*\_CN) and Western (*d*\_W) reference sets per image and metric.
- `derived_outputs/fusion/`
  - Baseline metric weights (subjective/objective/fused).
- `derived_outputs/dimfs/`
  - Dimension-level fused scores (DimFS) per image.
- `derived_outputs/validation/`
  - Released summaries for construct validity, direction convergent checks, and stability (relative CI).
- `metadata/`
  - Controlled vocabularies and mapping tables used to normalise style/site labels for the public release.
- `scripts/`
  - Minimal reproducibility scripts (pandas/numpy only).
- `audit/` (optional)
  - Small audit artefacts supporting internal consistency checks (does not require raw images).

## File naming and identifiers

- A runlog-to-release mapping table is provided in `metadata/file_map.csv`.
- Site label normalisation is documented in `metadata/site_alias_map_v1.csv`.
- `image_uid` is the stable identifier used across derived tables (pattern: `<stem>|<stem>`).

## Integrity

SHA-256 checksums for all tracked files (excluding the checksum file itself) are provided in `checksums_sha256.txt`.

## License

Code in `scripts/` is released under the license in `LICENSE`. Data products in `derived_outputs/` are provided for verification and reuse subject to the terms described in the manuscript’s data availability statement.

## How to cite

See `CITATION.cff` (update with a DOI after archiving on Zenodo/OSF/Figshare).


## Environment (recommended)

This release includes a minimal `environment.yml` for conda.

```bash
conda env create -f environment.yml
conda activate sfi-repro
```

You may also install via pip:

```bash
pip install -r requirements.txt
```


## Compressed mirrors

For convenience, a compressed mirror is provided:
- `derived_outputs/distances/DIST_master_long_public_v1.csv.gz` (mirror of the `.csv` used by the scripts).


## One-command verification

```bash
python scripts/verify_release.py --root .
```

This will (i) verify SHA256 checksums and (ii) regenerate `key_numbers.csv` and released tables under `repro_outputs/`.
