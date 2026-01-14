# Reference implementation + demo (Scheme 1: no redistribution of W prototypes)

This bundle contains a **lightweight** rights-cleared demo subset (images downscaled to max side 1600px, JPEG quality 80)
and a minimal CPU-only reference implementation.

## Demo inputs in this bundle
- `demo_data/Eva_Set/CH-AD|CH-BAR|CH-BYZ|CH-GOTH|CH-NEO/*`   (evaluation images; **5 per sub-style**)
- `demo_data/Ref_C/*`                                      (Chinese prototypes; flat folder)
- `demo_data/Ref_W/`                                       (empty; W prototypes are **user-supplied**)

## Run the demo
```bash
pip install -r requirements_reference_impl.txt
python scripts/run_reference_demo.py --eva-set demo_data/Eva_Set --ref-c demo_data/Ref_C --out reference_outputs
```

## Outputs
- `reference_outputs/DIST_demo_long.csv` (columns: `image_uid,image_path,style,style_abbrev,metric,dc,dw`)
- `reference_outputs/runlog_demo.json`

## Notes
This is a demonstration reference implementation and is not intended to reproduce the paper’s full results.
