#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Minimal CPU-only reference demo: images -> long-form directional distances.

This script is intentionally lightweight and uses only:
- numpy, pandas
- Pillow (PIL)

It implements *demo* versions of two metrics:
- Col_HSV-B_demo (global HSV histogram Bhattacharyya distance)
- Str_SSIM-D_demo (1 - SSIM on grayscale)

It pools distances to CN/W prototype pools by median, per image and metric,
and writes a long-form CSV compatible with the released schema.

NOTE: Western (W) prototypes are optional. If --ref-w is not provided, dw will be NaN.
"""

from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from PIL import Image


# ---- style mapping (folders -> paper-style labels) ----
FOLDER_TO_STYLE = {
    "CH-AD": ("Chinese_Art_Deco", "Ch-AD"),
    "CH-BAR": ("Chinese_Baroque", "Ch-BAR"),
    "CH-BYZ": ("Chinese_Byzantine_Revival", "Ch-BYZ"),
    "CH-GOTH": ("Chinese_Gothic_Revival", "Ch-GOTH"),
    "CH-NEO": ("Chinese_Neoclassical", "Ch-NEO"),
    # Ref_W often uses shorter codes
    "AD": ("Chinese_Art_Deco", "Ch-AD"),
    "BAR": ("Chinese_Baroque", "Ch-BAR"),
    "BYZ": ("Chinese_Byzantine_Revival", "Ch-BYZ"),
    "GOTH": ("Chinese_Gothic_Revival", "Ch-GOTH"),
    "NEO": ("Chinese_Neoclassical", "Ch-NEO"),
}

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def is_image(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in IMG_EXTS


def iter_images(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*") if is_image(p)])


def load_rgb(path: Path, size: int = 512) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    if size is not None:
        im = im.resize((size, size), resample=Image.BILINEAR)
    return np.asarray(im, dtype=np.uint8)


def load_gray(path: Path, size: int = 512) -> np.ndarray:
    im = Image.open(path).convert("L")
    if size is not None:
        im = im.resize((size, size), resample=Image.BILINEAR)
    arr = np.asarray(im, dtype=np.float32) / 255.0
    return arr


def hsv_hist_bhattacharyya(rgb_u8: np.ndarray, bins=(36, 10, 10)) -> np.ndarray:
    """Return normalized HSV histogram vector."""
    im = Image.fromarray(rgb_u8, mode="RGB").convert("HSV")
    hsv = np.asarray(im, dtype=np.uint8)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # H in [0,255] for PIL HSV; S,V in [0,255]
    hist, _ = np.histogramdd(
        np.stack([h, s, v], axis=-1).reshape(-1, 3),
        bins=bins,
        range=[(0, 256), (0, 256), (0, 256)],
    )
    hist = hist.astype(np.float64).ravel()
    hist_sum = hist.sum()
    if hist_sum > 0:
        hist /= hist_sum
    return hist


def bhattacharyya_distance(p: np.ndarray, q: np.ndarray, eps: float = 1e-12) -> float:
    """Bhattacharyya distance on discrete distributions."""
    # coefficient
    bc = float(np.sum(np.sqrt(np.clip(p, 0, 1) * np.clip(q, 0, 1))))
    bc = min(max(bc, eps), 1.0)
    return float(-np.log(bc))


def ssim(x: np.ndarray, y: np.ndarray) -> float:
    """Simple SSIM for grayscale images in [0,1]."""
    # Constants from original SSIM paper for L=1
    c1 = (0.01 ** 2)
    c2 = (0.03 ** 2)
    x = x.astype(np.float64)
    y = y.astype(np.float64)
    mu_x = x.mean()
    mu_y = y.mean()
    sigma_x = x.var()
    sigma_y = y.var()
    sigma_xy = ((x - mu_x) * (y - mu_y)).mean()
    num = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
    den = (mu_x ** 2 + mu_y ** 2 + c1) * (sigma_x + sigma_y + c2)
    return float(num / den) if den != 0 else 0.0


@dataclass
class EvalItem:
    image_path: Path
    style: str
    style_abbrev: str
    image_uid: str


def build_eval_items(eva_set: Path) -> List[EvalItem]:
    items: List[EvalItem] = []
    for style_dir in sorted([d for d in eva_set.iterdir() if d.is_dir()]):
        key = style_dir.name
        if key not in FOLDER_TO_STYLE:
            # skip unknown folders (or treat as generic)
            continue
        style, style_abbrev = FOLDER_TO_STYLE[key]
        for p in iter_images(style_dir):
            # stable uid: relative posix path from Eva_Set
            rel = p.relative_to(eva_set).as_posix()
            uid = f"demo/Eva_Set/{rel}"
            items.append(EvalItem(image_path=p, style=style, style_abbrev=style_abbrev, image_uid=uid))
    return items


def pool_prototypes_flat(ref_dir: Path) -> List[Path]:
    return iter_images(ref_dir)


def pool_prototypes_by_style(ref_w: Path) -> Dict[str, List[Path]]:
    pools: Dict[str, List[Path]] = {}
    for d in sorted([d for d in ref_w.iterdir() if d.is_dir()]):
        if d.name in FOLDER_TO_STYLE:
            style, style_abbrev = FOLDER_TO_STYLE[d.name]
            pools[style_abbrev] = iter_images(d)
    return pools


def median_pool_distance(distances: List[float]) -> float:
    if not distances:
        return float("nan")
    return float(np.median(np.asarray(distances, dtype=np.float64)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eva-set", type=str, required=True, help="Path to Eva_Set directory")
    ap.add_argument("--ref-c", type=str, required=True, help="Path to Ref_C directory (flat prototypes)")
    ap.add_argument("--ref-w", type=str, default=None, help="Optional path to Ref_W directory (style subfolders)")
    ap.add_argument("--out", type=str, default="reference_outputs", help="Output directory")
    ap.add_argument("--size", type=int, default=512, help="Resize images to size x size for demo metrics")
    args = ap.parse_args()

    eva_set = Path(args.eva_set).resolve()
    ref_c = Path(args.ref_c).resolve()
    ref_w = Path(args.ref_w).resolve() if args.ref_w else None
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    eval_items = build_eval_items(eva_set)
    if not eval_items:
        raise RuntimeError(f"No eval images found under {eva_set} with known style folders.")

    proto_c = pool_prototypes_flat(ref_c)
    if not proto_c:
        raise RuntimeError(f"No CN prototypes found under {ref_c}.")

    proto_w_pools = pool_prototypes_by_style(ref_w) if ref_w else {}

    # Precompute prototype representations for demo metrics
    # Col HSV hist
    proto_c_hsv = [(p, hsv_hist_bhattacharyya(load_rgb(p, size=args.size))) for p in proto_c]
    proto_w_hsv = {}
    if ref_w:
        for style_abbrev, pool in proto_w_pools.items():
            proto_w_hsv[style_abbrev] = [(p, hsv_hist_bhattacharyya(load_rgb(p, size=args.size))) for p in pool]

    # Str SSIM needs grayscale arrays
    proto_c_gray = [(p, load_gray(p, size=args.size)) for p in proto_c]
    proto_w_gray = {}
    if ref_w:
        for style_abbrev, pool in proto_w_pools.items():
            proto_w_gray[style_abbrev] = [(p, load_gray(p, size=args.size)) for p in pool]

    rows = []
    for item in eval_items:
        rgb = load_rgb(item.image_path, size=args.size)
        hsv = hsv_hist_bhattacharyya(rgb)

        gray = load_gray(item.image_path, size=args.size)

        # --- Metric 1: Col_HSV-B_demo ---
        dc_list = [bhattacharyya_distance(hsv, h2) for _, h2 in proto_c_hsv]
        dc = median_pool_distance(dc_list)

        dw = float("nan")
        if ref_w and item.style_abbrev in proto_w_hsv and proto_w_hsv[item.style_abbrev]:
            dw_list = [bhattacharyya_distance(hsv, h2) for _, h2 in proto_w_hsv[item.style_abbrev]]
            dw = median_pool_distance(dw_list)

        rows.append({
            "image_uid": item.image_uid,
            "image_path": item.image_path.as_posix(),
            "style": item.style,
            "style_abbrev": item.style_abbrev,
            "metric": "Col_HSV-B_demo",
            "dc": dc,
            "dw": dw,
        })

        # --- Metric 2: Str_SSIM-D_demo (distance = 1 - SSIM) ---
        dc_list = [1.0 - ssim(gray, g2) for _, g2 in proto_c_gray]
        dc = median_pool_distance(dc_list)

        dw = float("nan")
        if ref_w and item.style_abbrev in proto_w_gray and proto_w_gray[item.style_abbrev]:
            dw_list = [1.0 - ssim(gray, g2) for _, g2 in proto_w_gray[item.style_abbrev]]
            dw = median_pool_distance(dw_list)

        rows.append({
            "image_uid": item.image_uid,
            "image_path": item.image_path.as_posix(),
            "style": item.style,
            "style_abbrev": item.style_abbrev,
            "metric": "Str_SSIM-D_demo",
            "dc": dc,
            "dw": dw,
        })

    df = pd.DataFrame(rows)
    out_csv = out_dir / "DIST_demo_long.csv"
    df.to_csv(out_csv, index=False)

    runlog = {
        "eva_set": str(eva_set),
        "ref_c": str(ref_c),
        "ref_w": str(ref_w) if ref_w else None,
        "n_eval": int(len(eval_items)),
        "n_ref_c": int(len(proto_c)),
        "n_ref_w_total": int(sum(len(v) for v in proto_w_pools.values())) if ref_w else 0,
        "metrics": sorted(df["metric"].unique().tolist()),
        "image_size": int(args.size),
        "notes": "Demo reference implementation; not intended to reproduce paper results.",
    }
    (out_dir / "runlog_demo.json").write_text(json.dumps(runlog, indent=2), encoding="utf-8")

    print("Wrote:", out_csv)
    print("Wrote:", out_dir / "runlog_demo.json")
    print("Rows:", len(df))

if __name__ == "__main__":
    main()
