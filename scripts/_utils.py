from __future__ import annotations
from pathlib import Path
import hashlib
import pandas as pd
import numpy as np

POWER_MEAN_P = 0.55

def power_mean(values, p: float = POWER_MEAN_P) -> float:
    v = np.asarray(list(values), dtype=float)
    return (np.mean(np.power(v, p))) ** (1.0 / p)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def load_required_tables(root: Path):
    dist_path = root / "derived_outputs" / "distances" / "DIST_master_long_public_v1.csv"
    w_path = root / "derived_outputs" / "fusion" / "fusion_metric_weight_baseline_v1.csv"
    dimfs_path = root / "derived_outputs" / "dimfs" / "DimFS_long_v1.csv.gz"
    val_construct = root / "derived_outputs" / "validation" / "construct_validity_3set_summary_v1.csv"
    val_direction = root / "derived_outputs" / "validation" / "direction_convergent_summary_v1.csv"
    val_stability = root / "derived_outputs" / "validation" / "stability_relci_summary_v1.csv"

    for p in [dist_path, w_path, dimfs_path]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required file: {p.as_posix()}")

    dist = pd.read_csv(dist_path)
    w = pd.read_csv(w_path)
    dimfs = pd.read_csv(dimfs_path, compression="gzip")

    extras = {}
    if val_construct.exists():
        extras["construct_validity"] = pd.read_csv(val_construct)
    if val_direction.exists():
        extras["direction_convergent"] = pd.read_csv(val_direction)
    if val_stability.exists():
        extras["stability_relci"] = pd.read_csv(val_stability)

    return dist, w, dimfs, extras

def compute_metric_fs(dist: pd.DataFrame, p: float = POWER_MEAN_P) -> pd.DataFrame:
    df = dist.copy()
    df["p_cn"] = 1.0 - df["dc"].astype(float)
    df["p_w"] = 1.0 - df["dw"].astype(float)
    # power mean of two proximities
    df["FS"] = ((np.power(df["p_cn"], p) + np.power(df["p_w"], p)) / 2.0) ** (1.0 / p)
    return df

def compute_dimfs_from_dist(dist: pd.DataFrame, w: pd.DataFrame) -> pd.DataFrame:
    """Compute DimFS from metric-level fusion scores.

    Expects columns: image_uid, metric, FS, and either:
    - a 'dimension' column, or
    - a weights table providing metric->dimension mapping.
    """
    df = dist.copy()
    # Ensure dimension is present
    if "dimension" not in df.columns:
        df = df.merge(w[["metric", "dimension"]], on="metric", how="left")
    # Attach fused metric weights
    if "w_fuse" not in df.columns:
        df = df.merge(w[["metric", "w_fuse"]], on="metric", how="left")
    # normalise weights within each dimension
    df["w_dim"] = df.groupby("dimension")["w_fuse"].transform(lambda x: x / x.sum())
    dimfs_calc = (
        df.groupby(["image_uid", "dimension"], as_index=False)
          .apply(lambda g: pd.Series({"DimFS_calc": np.average(g["FS"].to_numpy(), weights=g["w_dim"].to_numpy())}))
          .reset_index(drop=True)
    )
    return dimfs_calc


def compute_image_mfs(dist: pd.DataFrame, w: pd.DataFrame) -> pd.DataFrame:
    """Compute image-level metric-fused score (MFS) across 8 metrics."""
    df = dist.copy()
    if "w_fuse" not in df.columns:
        w_map = w.set_index("metric")["w_fuse"]
        df["w_fuse"] = df["metric"].map(w_map)
    mfs = (
        df.groupby("image_uid", as_index=False)
          .apply(lambda g: pd.Series({"MFS": np.average(g["FS"].to_numpy(), weights=g["w_fuse"].to_numpy())}))
          .reset_index(drop=True)
    )
    return mfs

