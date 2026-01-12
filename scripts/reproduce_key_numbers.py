#!/usr/bin/env python3
"""Reproduce key summaries from the public SFI release.

This script re-computes:
- metric-level fusion scores (FS) from directional distances (dc, dw)
- image-level metric-fused score (MFS) using fused metric weights
- dimension-level scores (DimFS) and agreement vs released DimFS table
- directional consistency summaries (how often dc < dw)

It does NOT require raw images or GPU.
"""

from __future__ import annotations
from pathlib import Path
import argparse
import pandas as pd

from _utils import (
    POWER_MEAN_P,
    load_required_tables,
    compute_metric_fs,
    compute_dimfs_from_dist,
    compute_image_mfs,
    sha256_file,
)

def verify_checksums(root: Path, out_dir: Path) -> None:
    checksum_file = root / "checksums_sha256.txt"
    if not checksum_file.exists():
        return
    bad = []
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        h, rel = line.split(None, 1)
        rel = rel.strip()
        p = root / rel
        if not p.exists():
            bad.append((rel, "missing"))
            continue
        h2 = sha256_file(p)
        if h2.lower() != h.lower():
            bad.append((rel, "mismatch"))
    pd.DataFrame(bad, columns=["path", "status"]).to_csv(out_dir / "checksum_verification.csv", index=False)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, default=".", help="Release bundle root directory")
    ap.add_argument("--out", type=str, default="repro_outputs", help="Output directory")
    ap.add_argument("--verify-checksums", action="store_true", help="Verify checksums_sha256.txt if present")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.verify_checksums:
        verify_checksums(root, out_dir)

    dist, w, dimfs_release, extras = load_required_tables(root)

    # Compute FS / MFS / DimFS
    dist_fs = compute_metric_fs(dist, p=POWER_MEAN_P)

    dimfs_calc = compute_dimfs_from_dist(dist_fs, w)
    dimfs_cmp = dimfs_calc.merge(
        dimfs_release[["image_uid", "dimension", "DimFS"]],
        on=["image_uid", "dimension"],
        how="left",
    )
    dimfs_cmp["abs_diff"] = (dimfs_cmp["DimFS_calc"] - dimfs_cmp["DimFS"]).abs()

    # MFS (image-level, across 8 metrics)
    mfs = compute_image_mfs(dist_fs, w)

    # Directional consistency: closer to CN if dc < dw
    dist_fs = dist_fs.merge(w[["metric", "dimension"]], on="metric", how="left")
    dist_fs["closer_CN"] = (dist_fs["dc"].astype(float) < dist_fs["dw"].astype(float)).astype(int)

    metric_dir = (
        dist_fs.groupby("metric", as_index=False)
        .agg(
            n=("image_uid", "nunique"),
            p_closer_CN=("closer_CN", "mean"),
            mean_dc=("dc", "mean"),
            mean_dw=("dw", "mean"),
        )
    )
    metric_dir["mean_dw_minus_dc"] = metric_dir["mean_dw"] - metric_dir["mean_dc"]

    dim_dir = (
        dist_fs.groupby("dimension", as_index=False)
        .agg(
            n=("image_uid", "nunique"),
            p_closer_CN=("closer_CN", "mean"),
            mean_dc=("dc", "mean"),
            mean_dw=("dw", "mean"),
        )
    )
    dim_dir["mean_dw_minus_dc"] = dim_dir["mean_dw"] - dim_dir["mean_dc"]

    # Key numbers (compact)
    keys = []
    keys.append(("n_images", int(dist_fs["image_uid"].nunique())))
    keys.append(("n_metrics", int(dist_fs["metric"].nunique())))
    keys.append(("n_dimensions", int(dimfs_release["dimension"].nunique())))
    keys.append(("power_mean_p", float(POWER_MEAN_P)))
    keys.append(("mfs_mean", float(mfs["MFS"].mean())))
    keys.append(("mfs_median", float(mfs["MFS"].median())))
    keys.append(("dimfs_absdiff_mean", float(dimfs_cmp["abs_diff"].mean())))
    keys.append(("dimfs_absdiff_max", float(dimfs_cmp["abs_diff"].max())))
    keys.append(("direction_p_closer_CN_overall", float(dist_fs["closer_CN"].mean())))

    key_df = pd.DataFrame(keys, columns=["key", "value"])
    key_df.to_csv(out_dir / "key_numbers.csv", index=False)

    # Save detailed outputs
    dimfs_cmp.to_csv(out_dir / "dimfs_agreement.csv", index=False)
    metric_dir.to_csv(out_dir / "directional_summary_by_metric.csv", index=False)
    dim_dir.to_csv(out_dir / "directional_summary_by_dimension.csv", index=False)

    # Compact per-style DimFS summary
    dimfs_style = (
        dimfs_release.groupby(["style_abbrev", "dimension"], as_index=False)
        .agg(
            n=("image_uid", "nunique"),
            mean_DimFS=("DimFS", "mean"),
            median_DimFS=("DimFS", "median"),
        )
        .sort_values(["style_abbrev", "dimension"])
    )
    dimfs_style.to_csv(out_dir / "dimfs_summary_by_style_dimension.csv", index=False)

    # Include released validation summaries (verbatim) if present
    for name, df in extras.items():
        df.to_csv(out_dir / f"released_{name}.csv", index=False)

    (out_dir / "RUN_NOTES.txt").write_text(
        "\n".join([
            f"POWER_MEAN_P={POWER_MEAN_P}",
            "Note: City-level calibrated SFI is not recomputed here because city aggregation and calibration parameters are not part of this public release.",
        ]) + "\n",
        encoding="utf-8",
    )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
