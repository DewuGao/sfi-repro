# Derived outputs generation pipeline (pseudocode specification)

**Recommended location in the public package:** `docs/DERIVED_OUTPUTS_PIPELINE_PSEUDOCODE.md`  
**Purpose:** Provide an auditable, implementation-independent specification of how the released *derived outputs* are generated from rights-restricted raw façade images, using frozen parameters in **Supplementary Data 1**.

This document is a **specification** (what steps are performed and what parameters are fixed), not a full code release. A reference implementation (if provided) should be treated as one possible realization of this specification.

---

## Scope and inputs

### Inputs (conceptual)
- Evaluation façade images (*EVAL*, *n* = 2406)
- Two prototype pools:
  - Chinese reference set (*CN*)
  - Western reference set (*W*)
- Optional image geometry metadata per image (if available):
  - 4-point quadrilateral for perspective rectification; and/or
  - ROI bounding box for façade cropping

### Outputs (released tables; schema-level)
This specification targets the release-format tables located under:

- `derived_outputs/distances/`  
  - `DIST_master_long_public_v1.csv(.gz)` — long-form, per-image × per-metric directional distances to CN/W
- `derived_outputs/dimfs/`  
  - `DimFS_long_v1.csv.gz` — long-form, per-image × per-dimension fusion scores
- `derived_outputs/validation/`  
  - summary CSVs used for verification of reported results

Supporting metadata:
- `metadata/style_map_v1.csv` — stable style labels/abbreviations
- `metadata/metric_to_dimension_v1.csv` — metric → dimension mapping
- `derived_outputs/fusion/fusion_metric_weight_baseline_v1.csv` — baseline fused weights

---

## Frozen parameters (from Supplementary Data 1)

### Preprocessing
- EXIF orientation correction: `True`
- ICC to sRGB conversion: `True`
- Perspective rectification:
  - enabled: `True`, method: `four_point`, post-crop margin: `0.02`
- ROI cropping:
  - ROI applied: `True`, fallback: `center_crop_or_pad`
- White balance:
  - method order: `['gray_card', 'gray_world']`
  - neutral threshold: `0.02`
  - skip if insufficient neutral pixels: `True`
- CLAHE (luminance only):
  - clip limit: `2.0`, tile grid: `[8, 8]`, channel: `luminance`
- Resize to `[512, 512]`:
  - interpolation: `bilinear`, antialias: `True`
  - aspect preserved: `True`, crop/pad: `center`, pad color: `neutral_gray`
  - single-pass resize: `True`

### Metric computation (8 metrics; pooled by median)
- Prototype-pool aggregation for each direction: `median`
- Metric set: `gram_d, glcm_c, ssim_d, eh_d, hsv_b, hsv_m, lpips_o, clip_s`
- Similarity→distance unification: `d = 1 - s`

### Alignment (order-preserving)
- Method: `rank_percentile` (domain: `evaluation_set`)
- Per-direction mapping: `True`
- Tie handling: `average`
- Endpoints: `clip_to_[0,1]`

### Fusion and calibration
- Winsorization cap: `P99.7`
- Symmetric concave fusion (power mean): exponent *p* = `0.55`
- Subjective/objective weight mix: *q* = `0.4`  
  (*w* = (1−q)·w_AHP + q·w_entropy; then normalized)
- City balance factor (city aggregation only): γ = `0.7`
- Calibration anchors (monotone mapping SFI0→SFIc):
  - Q60: SFI0 = `0.487584858053780` -> SFIc = `0.70`
  - Q95: SFI0 = `0.596475433063520` -> SFIc = `0.85`

---

## Pseudocode

### Notation
- `x` : an evaluation image (after preprocessing)
- `p` : a prototype image (after preprocessing)
- `m` : a metric in the 8-metric suite
- `d_CN_raw(x,m,p)` : raw distance between `x` and prototype `p` in the CN pool for metric `m`
- `d_CN_raw(x,m)` : pooled distance to the CN pool (median over prototypes)
- `dc(x,m)` : aligned distance to CN pool in (0,1) after rank-percentile mapping  
  (analogously `dw(x,m)` for the W pool)
- `FS(x,m)` : metric-level fusion score
- `DimFS(x,dim)` : dimension-level fusion score (dim ∈ {texture, structure, colour, perceptual, semantic})
- `SFI0(x)` : image-level fused score before calibration
- `SFIc(x)` : calibrated score on the fixed reporting scale

---

### Step 0 — Load frozen configuration and metadata
```text
cfg        <- load_yaml("Supplementary_Data_1.yaml")
map_style  <- read_csv("metadata/style_map_v1.csv")
map_dim    <- read_csv("metadata/metric_to_dimension_v1.csv")
w_baseline <- read_csv("derived_outputs/fusion/fusion_metric_weight_baseline_v1.csv")
```

---

### Step 1 — Preprocess all images (evaluation + prototypes)

```text
function PREPROCESS(I_raw, meta):
    I <- apply_exif_orientation(I_raw)                          if cfg.preprocessing.exif_orientation
    I <- convert_icc_to_srgb(I)                                 if cfg.preprocessing.icc_to_srgb

    if cfg.preprocessing.perspective_rectify.enabled AND meta has 4-point corners:
        I <- four_point_rectify(I, meta.corners)
        I <- crop_margin(I, margin = 0.02)

    if cfg.preprocessing.roi_applied AND meta has ROI:
        I <- crop_to_roi(I, meta.roi)
    else:
        I <- center_crop_or_pad(I)                              # fallback

    I <- white_balance(I,
            method_order = ["gray_card","gray_world"],
            neutral_threshold = 0.02,
            skip_if_insufficient_neutral = True)

    I <- clahe_on_luminance(I, clip_limit = 2.0, tile_grid = [8,8])

    I <- resize(I,
            target = [512,512],
            interpolation = "bilinear",
            antialias = True,
            aspect_preserving = True,
            crop_or_pad = "center",
            pad_color = "neutral_gray",
            single_pass = True)

    return I
```

Apply to all images:
```text
EVAL_pre <- PREPROCESS_ALL(EVAL, meta_EVAL)
CN_pre   <- PREPROCESS_ALL(CN_pool, meta_CN)
W_pre    <- PREPROCESS_ALL(W_pool,  meta_W)
```

---

### Step 2 — Compute pooled directional distances to prototype pools (per metric)

For each evaluation image and each metric:
```text
function DIST_TO_POOL(x, POOL, metric m):
    values <- []
    for p in POOL:
        s_or_d <- metric_compare(x, p, m)              # may output similarity or distance
        d <- to_distance(s_or_d, rule = "d = 1 - s")   # unify where applicable
        append(values, d)
    return median(values)                              # pool aggregation
```

Compute raw pooled distances:
```text
for each x in EVAL_pre:
    for each m in METRICS:
        dCN_raw[x,m] <- DIST_TO_POOL(x, CN_pre, m)
        dW_raw [x,m] <- DIST_TO_POOL(x, W_pre,  m)
```

---

### Step 3 — Rank-percentile alignment to (0,1) within evaluation set (per metric × direction)

Order-preserving mapping is computed **within the evaluation set**:
```text
function RANK_PERCENTILE_ALIGN(vector V):
    r <- percentile_rank(V, tie_handling = "average")   # order-preserving
    return clip(r, 0.0, 1.0)
```

Apply per metric and per direction:
```text
for each m in METRICS:
    dc[:,m] <- RANK_PERCENTILE_ALIGN(dCN_raw[:,m])
    dw[:,m] <- RANK_PERCENTILE_ALIGN(dW_raw [:,m])
```

Export the release-format long table:
```text
write_long_csv("derived_outputs/distances/DIST_master_long_public_v1.csv",
    columns = [image_uid, style, style_abbrev, metric, dc, dw])
```

---

### Step 4 — Winsorize aligned distances (cap at P99.7) before fusion

```text
function WINSORIZE_CAP(V, percentile = 99.7):
    cap <- quantile(V, 0.997)
    return elementwise_min(V, cap)

for each m in METRICS:
    dc[:,m] <- WINSORIZE_CAP(dc[:,m], 99.7)
    dw[:,m] <- WINSORIZE_CAP(dw[:,m], 99.7)
```

---

### Step 5 — Metric-level fusion score FS(x,m) from two directional proximities

Convert distances to proximities:
```text
pCN <- 1 - dc
pW  <- 1 - dw
```

Symmetric concave power mean (p = 0.55):
```text
function POWER_MEAN(a, b, p):
    return ((a^p + b^p)/2)^(1/p)

for each x, m:
    FS[x,m] <- POWER_MEAN(pCN[x,m], pW[x,m], p = 0.55)
```

---

### Step 6 — Dimension-level fusion (DimFS) and export

Use metric->dimension mapping (`metadata/metric_to_dimension_v1.csv`) and baseline fused weights (`derived_outputs/fusion/fusion_metric_weight_baseline_v1.csv`). Let `w_fuse(m)` denote the baseline fused weight for metric `m`.

Within each dimension, normalize weights to sum to 1 and aggregate:
```text
for each x, each dim:
    M_dim <- metrics_in_dimension(dim, map_dim)
    w_norm[m] <- w_fuse(m) / sum_over_k_in(M_dim) w_fuse(k)
    DimFS[x,dim] <- sum_over_m_in(M_dim) w_norm[m] * FS[x,m]
```

Export:
```text
write_long_csv_gz("derived_outputs/dimfs/DimFS_long_v1.csv.gz",
    columns = [image_uid, style, style_abbrev, dimension, DimFS])
```

---

### Step 7 — (Optional) Image-level SFI0 and calibrated SFIc

Image-level fusion:
```text
for each x:
    SFI0[x] <- sum_over_all_metrics w_fuse(m) * FS[x,m]
```

Monotone calibration (anchors from SD1):
```text
SFIc[x] <- monotone_map(SFI0[x],
            anchors = [("Q60", 0.487584858053780, 0.70),
                       ("Q95", 0.596475433063520, 0.85)],
            domain = [0,1],
            range  = [0,1])
```

(Seven-level semantic grades are assigned by binning `SFIc` into fixed intervals declared in SD1.)

---

### Step 8 — Validation summaries (release verification layer)

Validation criteria, thresholds, and seeds are frozen in **Supplementary Data 2**; run provenance and validation outcomes are recorded in **Supplementary Data 3**. Summary CSVs used for independent verification are exported to:

- `derived_outputs/validation/construct_validity_3set_summary_v1.csv`
- `derived_outputs/validation/direction_convergent_summary_v1.csv`
- `derived_outputs/validation/stability_relci_summary_v1.csv`

---

## Determinism and provenance (recommended)

When implementing this specification, record:
- library versions (minimums in SD1; exact versions recommended when archiving),
- pipeline seed(s) (SD1 declares a default; SD2 declares validation-specific seeds),
- hashes of input file lists (evaluation + prototype pools),
- a runlog capturing the above and the output file manifest.

---

## Rights and access boundary (context)
Raw façade images are not included in the public reproducibility release due to third-party rights constraints. This specification exists to maximise transparency of the derived-output generation process while respecting those constraints.
