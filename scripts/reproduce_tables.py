#!/usr/bin/env python3
"""Generate table-like CSV outputs from the public SFI release.

This script produces compact CSVs that correspond to common review checks:
- metric weights
- directionality summaries
- DimFS summaries (overall and by sub-style)
- constructs/validation summaries (verbatim copies)
"""

from __future__ import annotations
from pathlib import Path
import argparse
import pandas as pd
import numpy as np

from _utils import load_required_tables, compute_metric_fs, compute_image_mfs, POWER_MEAN_P

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, default=".", help="Release bundle root directory")
    ap.add_argument("--out", type=str, default="repro_outputs/tables", help="Output directory for table CSVs")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    dist, w, dimfs_release, extras = load_required_tables(root)
    dist_fs = compute_metric_fs(dist, p=POWER_MEAN_P).merge(
        w[["metric", "dimension", "w_fuse"]], on="metric", how="left"
    )

    # 1) Metric weights
    w.sort_values("w_fuse", ascending=False).to_csv(out_dir / "table_metric_weights.csv", index=False)

    # 2) Image-level MFS summary
    mfs = compute_image_mfs(dist_fs, w).merge(
        dist[["image_uid", "style_abbrev"]].drop_duplicates(), on="image_uid", how="left"
    )
    mfs_summary = (
        mfs.groupby("style_abbrev", as_index=False)
        .agg(n=("image_uid", "nunique"), mean_MFS=("MFS", "mean"), median_MFS=("MFS", "median"))
        .sort_values("mean_MFS", ascending=False)
    )
    mfs_summary.to_csv(out_dir / "table_mfs_summary_by_style.csv", index=False)

    # 3) Directionality summaries
    dist_fs["closer_CN"] = (dist_fs["dc"].astype(float) < dist_fs["dw"].astype(float)).astype(int)
    metric_dir = (
        dist_fs.groupby(["dimension", "metric"], as_index=False)
        .agg(n=("image_uid", "nunique"), p_closer_CN=("closer_CN", "mean"), mean_dc=("dc", "mean"), mean_dw=("dw", "mean"))
    )
    metric_dir["mean_dw_minus_dc"] = metric_dir["mean_dw"] - metric_dir["mean_dc"]
    metric_dir.to_csv(out_dir / "table_directional_by_metric.csv", index=False)

    dim_dir = (
        dist_fs.groupby("dimension", as_index=False)
        .agg(n=("image_uid", "nunique"), p_closer_CN=("closer_CN", "mean"), mean_dc=("dc", "mean"), mean_dw=("dw", "mean"))
    )
    dim_dir["mean_dw_minus_dc"] = dim_dir["mean_dw"] - dim_dir["mean_dc"]
    dim_dir.to_csv(out_dir / "table_directional_by_dimension.csv", index=False)

    # 4) DimFS summaries
    dim_overall = (
        dimfs_release.groupby("dimension", as_index=False)
        .agg(
            n=("image_uid", "nunique"),
            mean_DimFS=("DimFS", "mean"),
            median_DimFS=("DimFS", "median"),
            q25_DimFS=("DimFS", lambda x: float(np.quantile(x, 0.25))),
            q75_DimFS=("DimFS", lambda x: float(np.quantile(x, 0.75))),
        )
        .sort_values("dimension")
    )
    dim_overall.to_csv(out_dir / "table_dimfs_summary_overall.csv", index=False)

    dim_style = (
        dimfs_release.groupby(["style_abbrev", "dimension"], as_index=False)
        .agg(n=("image_uid", "nunique"), mean_DimFS=("DimFS", "mean"), median_DimFS=("DimFS", "median"))
        .sort_values(["style_abbrev", "dimension"])
    )
    dim_style.to_csv(out_dir / "table_dimfs_summary_by_style.csv", index=False)

    # 5) Validation summaries (verbatim copies)
    for name, df in extras.items():
        df.to_csv(out_dir / f"table_released_{name}.csv", index=False)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
