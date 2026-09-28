# Model card — AquaSentinel stream health-risk estimator

## Overview
A regularized linear model that estimates the three OneAquaHealth stream
health-risk components (pathogen, faecal, ARG) from landscape and climate context,
with distribution-free prediction intervals. Built for **screening and
prioritisation**, explicitly **not** for diagnosis or absolute prediction.

## Data
- 96 monitoring sites with lab risk targets, across 5 EU cities.
- Features: 5 log-transformed distances, 48 landscape-buffer features (6 families ×
  8 radii), 4 climate summaries, nitrate, altitude → 59 features.
- **Cross-sectional snapshot** (one sample per site, 2023). No temporal dimension.

## Method
- **Estimator:** `ElasticNetCV` (impute median → standardize → elastic-net with
  inner 5-fold CV over `l1_ratio ∈ {0.2,0.5,0.9,1.0}`). Elastic-net chosen for
  interpretability and its L2 grouping of collinear buffer families.
- **Targets:** the three risk components; composite = mean of component predictions.
- **Uncertainty:** split-conformal intervals (80%); calibration on a 24-site
  held-out split. Half-widths ≈ 0.21 (pathogen), 0.33 (faecal), 0.23 (ARG) on the
  0–1 scale — deliberately wide, reflecting real predictive limits.
- **Explanation:** standardized coefficient × standardized feature value per site,
  surfaced as plain-language drivers.

## Validation
Two schemes, both against a **city-mean / global-mean baseline**:
- **Leave-one-city-out (LOCO)** — the real question: does it transfer to a new city?
- **Random 5-fold** — within-distribution performance.

| Target | LOCO MAE | Baseline MAE | Beats baseline (MAE)? | LOCO Spearman | K-fold Spearman |
|---|---|---|---|---|---|
| Pathogen | 0.151 | 0.148 | **No** | 0.399 | 0.274 |
| Faecal | 0.156 | 0.153 | **No** | −0.091 | −0.103 |
| ARG | 0.129 | 0.128 | **No** | −0.328 | 0.076 |
| Composite | 0.104 | 0.100 | **No** | 0.282 | 0.020 |

Shallow gradient boosting (secondary check) also fails to beat baseline on MAE
(LOCO MAE 0.105 vs 0.100; K-fold 0.112 vs 0.100).

## Honest headline finding
**On absolute error (MAE), neither the linear nor the gradient-boosted model beats a
city-mean baseline for any target.** Landscape features carry only a **weak,
inconsistent rank signal**: positive for pathogen (LOCO ρ=0.40) and composite
(ρ=0.28), but negative for faecal and ARG. Risk is strongly city-structured, and
features that correlate with a city stop helping once that city is held out.

**Consequence for the product:** the model is used only for (1) plain-language
*explanation* of associations, (2) *coarse pathogen/composite prioritisation* with
wide intervals, and (3) *scenario direction*. Site health cards lead with **observed
lab values**, not model predictions. We never present the model as a precise or
trustworthy absolute predictor, and we never make "safe to swim" claims.

## Descriptive associations (Spearman, n=96, all weak but several significant)
- Vegetation fragmentation @250 m: ρ = **+0.28** (p=0.006)
- Distance to wastewater stations: ρ = **−0.22** (p=0.028)
- Distance to crop fields: ρ = −0.22; to hospitals: ρ = −0.21
- Impervious surface @2 km: ρ = +0.18
These are **associational, not causal**, and the effect sizes are small.

## Intended users & use
Municipal water/health officers and researchers prioritising inspection effort;
citizen scientists getting a coarse screening band for a new site. Operating
envelope: the five partner cities. Not validated elsewhere.

## Limitations & ethics
- Cross-sectional data → no forecasting; "early warning" is a scenario engine plus a
  real-time-ingestion design, not a fitted temporal model.
- n=96 with city structure → poor cross-city transfer (shown above).
- Coordinate-swap detection only catches swaps that land in a partner country;
  swaps that stay out-of-region (e.g. some Brazilian entries) are flagged only as
  out-of-region. Documented, not hidden.
- Scaled 0–1 risks are relative indices, not calibrated probabilities of harm.
- No personal data is used. Environmental screening only.

## Reproducibility
`make analyze` regenerates every number, figure, and the model artifact from the
raw CSVs. Random seed fixed (42).
