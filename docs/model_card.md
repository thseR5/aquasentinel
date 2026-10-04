# Model card — landscape model

## What it is, and what it is not
A regularised linear model that relates the three OneAquaHealth risk components
(pathogen, faecal, ARG) to landscape and climate context. It was built to test one
question: **can landscape data predict stream health risk at a site that has not been
sampled?** On this data the answer is no. The model is therefore used only to show
exploratory landscape context on the site health card. AquaSentinel does not forecast
risk and does not rank unsampled sites.

## Data
- 96 monitoring sites with lab risk values, in 5 cities.
- 59 features: 5 log-transformed distances, 48 landscape-buffer features (6 families ×
  8 radii from 50 m to 2 km), 4 climate summaries, nitrate, altitude.
- A snapshot: one sample per site, each city sampled in a single campaign between May
  and September 2023.

## Method
- `ElasticNetCV`: median imputation → standardisation → elastic-net, with inner 5-fold
  cross-validation over the penalty and `l1_ratio ∈ {0.2, 0.5, 0.9, 1.0}`.
- One model per component. The composite estimate is the mean of the three.
- Explanation: standardised coefficient × standardised feature value per site.
- Intervals: split-conformal, 80%, calibrated on 24 held-out sites. They are valid for
  sites exchangeable with those 96, not for a new city.

## Validation
**Leave-one-city-out**: train on four cities, test on the fifth. The baseline predicts
the mean of the four training cities, so it never sees the held-out city either.

| Target | Model error (MAE) | Baseline error | Beats baseline? | Rank agreement inside the held-out city |
|---|---|---|---|---|
| Pathogen | 0.160 | 0.148 | No | +0.13 |
| Faecal | 0.157 | 0.153 | No | +0.03 |
| ARG | 0.129 | 0.128 | No | −0.05 |
| Composite | 0.107 | 0.103 | No | +0.20 |

Rank agreement is the Spearman correlation between predicted and observed values
*inside* each held-out city, averaged over the five cities. For the composite it ranges
from −0.15 (Ghent) to +0.63 (Benevento). Pooling all predictions into one correlation
would mix in between-city offsets and overstate skill, so we do not report it as the
headline.

For faecal risk the figure comes from four cities and for ARG from one: in the other
held-out cities the model predicts a constant, so there is no ranking to score.

Random 5-fold cross-validation tells the same story: composite error 0.104 against a
baseline of 0.101. Pathogen and ARG edge their baselines by 0.002 and 0.001, which is
noise. Shallow gradient boosting is no better (leave-one-city-out composite
error 0.105 against 0.103; rank agreement +0.03).

## What the fitted model contains
- Pathogen: 10 non-zero coefficients. The largest are distance to wastewater stations
  (negative) and peak rainfall (positive; a station-level value shared by many sites, so
  mostly a city marker).
- Faecal: **0 non-zero coefficients.** The penalty removes every feature and the model
  predicts a constant.
- ARG: 8 small non-zero coefficients.
- 80% interval half-widths: pathogen 0.19, faecal 0.21, ARG 0.18, composite 0.11, on a
  0 to 1 scale where the composite's standard deviation is about 0.13.

## Consequence for the product
- No forecasting, no scenario simulation, no estimated risk for unsampled sites. An
  earlier version had these; they were removed after this validation.
- The health card shows observed lab values. Landscape factors appear in a collapsed
  "exploratory" section.
- The negative result is published as an insight (`INS-MODEL-01`).

## Limits and ethics
- 96 sites and five cities is a small test. A larger network or repeated sampling may
  reveal signal this snapshot cannot.
- The scaled 0 to 1 risks are relative indices defined by OneAquaHealth, not calibrated
  probabilities of harm.
- No personal data is used. Environmental screening only.

## Reproducibility
`make analyze` regenerates `outputs/cv_results.json`, `outputs/model_summary.json`,
`outputs/gbm_comparison.json` and the model file. Random seed 42.
