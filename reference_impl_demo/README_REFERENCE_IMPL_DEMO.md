# Reference implementation + demo (Scheme X / ULTRALITE)

This folder bundles a **minimal reference implementation** and a **small demo dataset** for the SFI pipeline.

- **Scheme X (ULTRALITE)**: the demo includes **Chinese reference set (Ref_C)** but **does not include Western prototypes (Ref_W)**.
  - Therefore, the demo output column `dw` is expected to be **empty/NaN for all rows**.
  - The column `dc` is computed normally.

## Quick run (Windows / Anaconda Prompt)

1) Install minimal deps for the reference demo:
   - `pip install -r requirements_reference_impl.txt`

2) Run the demo:
   - `python scripts\run_reference_demo.py --eva-set demo_data\Eva_Set --ref-c demo_data\Ref_C --out reference_outputs`

3) Verify demo dataset integrity (optional):
   - `python scripts\\verify_demo_manifest.py --root demo_data`

4) Verify evidence artifacts inside `reference_outputs/`:
   - `python scripts\make_reference_outputs_checksums.py`
   - Then verify with the top-level checker (from repo root):
     - `python scripts\verify_checksums.py --root reference_impl_demo --checksums reference_outputs\checksums_sha256_reference_outputs.txt --strict`

## Notes

- The demo dataset is small by design; it is meant to validate **file structure + pipeline wiring + deterministic outputs**.
- For full reproduction, use the main repo scripts and derived outputs in the repository root.
