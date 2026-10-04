# Insight Discovery Engine

AquaSentinel's core is not a predictor. It is an engine that **discovers** candidate
insights, **challenges** them, and gives each a **verdict**. The rule is enforced in code
(`src/aquasentinel/insights.py`) and in tests: every insight carries a statistic, a
sample size, a scope, a limitation, a next step and the record of how it was challenged.

Reproduce: `make insights` (writes `outputs/insights.json`). The run is seeded and
deterministic; `tests/test_insights.py::test_engine_is_reproducible` checks it.

## Three verdicts

| Verdict | Meaning | What to do with it |
|---|---|---|
| **Supported** | Survived every challenge that applies | Act on it |
| **Exploratory** | Survived the city check but not the multiple-testing correction | A hypothesis: test it on new samples before acting |
| **Rejected** | Failed the challenge | Keep it out of decisions |

## What is discovered

| Kind | Method |
|---|---|
| Relationship between risk dimensions | Spearman correlation with a 1,000-resample bootstrap interval, repeated inside cities |
| Observed risk profiles | K-means on the standardised pathogen / faecal / ARG values; k chosen by silhouette |
| Landscape associations | Spearman of each of 59 landscape and climate features against composite risk; the 6 strongest are reported |
| Composite contradictions | Sites where one component is at least 0.35 above the composite |
| Within-city outliers | Sites at least 1.5 SD above their own city's mean |
| Cross-city differences | Kruskal–Wallis per component and on the composite |
| Model transfer | Leave-one-city-out validation against a training-mean baseline |
| Citizen data quality | Deterministic rules on the citizen site registrations |

## How each is challenged

**Associations face two challenges.**

1. *City confounding.* The city mean is removed from both variables and the correlation
   is recomputed. To pass, the within-city |ρ| must be at least 0.15 with p < 0.10. An
   association that exists only between cities is rejected.
2. *Multiple testing.* Picking the strongest of 59 features guarantees some will look
   significant. Composite risk is shuffled between sites of the same city 500 times,
   and each time the strongest within-city |ρ| across all 59 features is recorded. That
   is the yardstick for "how good does the best of 59 look by chance". In this data it
   reaches 0.32 in 5% of shuffles. An association is supported only if its family-wise
   p-value is below 0.05. Otherwise it stays exploratory.

**Observed risk profiles** are compared with 200 simulated datasets drawn from a
multivariate normal with the same means and correlations, which therefore contain no
clusters. The simulation is allowed the same choice of k as the real data. This is
stricter than shuffling each column, which only tests whether the components are
correlated.

**The "no association" headline** rests on a bootstrap confidence interval that spans
zero and stays near zero inside cities, and on the contrast with the pathogen–faecal
correlation, which is strongly positive in all five cities.

**Cross-city differences** are tested per component with a Holm correction across the
three tests.

## What the engine found

14 insights: 7 supported, 4 exploratory, 3 rejected.

| Insight | Evidence | Verdict |
|---|---|---|
| No detectable association between ARG and faecal risk | ρ = −0.03, 95% CI −0.22 to +0.17; 0.00 inside cities. Pathogen–faecal ρ = +0.72 (CI +0.60 to +0.82), positive in 5/5 cities. A composite watchlist misses 18 of the 24 highest-ARG sites | **Supported** |
| Cities differ on each risk dimension; the composite hides it | Composite p = 0.060. Per component, Holm-adjusted: pathogen p < 0.001, faecal p = 0.029, ARG p = 0.029. Coimbra highest for pathogen (0.32), Oslo for ARG (0.44) | **Supported** |
| Two observed risk profiles emerge | 31 sites with elevated pathogen and faecal, 65 with low; ARG average in both. Silhouette 0.380 against a simulated mean of 0.331; p = 0.015 | **Supported** |
| Composite hides one very high component | 6 sites, for example T17 (composite 0.53, faecal 1.00) and T10 (composite 0.23, ARG 0.64) | **Supported** |
| Within-city hotspots | 9 sites; C5 and BN2 are 2.6 SD above their city mean | **Supported** |
| Landscape does not predict risk in an unseen city | The model beats the baseline for 0 of 4 targets (composite error 0.107 against 0.103) | **Supported** (a negative result) |
| 42% of citizen registrations need fixing | 30 of 71: 10 test names, 3 swapped coordinates, 19 duplicates of 5 places | **Supported** |
| Vegetation fragmentation within 250 m | ρ = +0.28; inside cities +0.18 (p = 0.078), same sign in 5/5 cities; family-wise p = 0.90 | **Exploratory** |
| Distance to wastewater stations | ρ = −0.22; inside cities −0.23 (p = 0.021), 4/5 cities; family-wise p = 0.45 | **Exploratory** |
| Landscape fragmentation within 1500 m | ρ = −0.20; inside cities −0.25 (p = 0.015), 3/5 cities; family-wise p = 0.34 | **Exploratory** |
| High-risk sites the landscape candidates do not explain | BN4, BN15, T6. Built on exploratory patterns, so exploratory itself | **Exploratory** |
| Distance to crop fields | ρ = −0.22 overall, −0.06 inside cities | **Rejected** |
| Distance to hospitals | ρ = −0.21 overall, −0.06 inside cities | **Rejected** |
| Vegetation fragmentation within 500 m | ρ = +0.20 overall, +0.01 inside cities | **Rejected** |

## What this means for a decision-maker

- Rank and triage sites on ARG separately. The composite score and faecal indicators
  will not find the high-ARG sites.
- Compare cities component by component, not on the composite.
- Do not use landscape features to rank sites that have not been sampled. Send
  samplers instead.
- Treat the three landscape candidates as hypotheses for the next sampling campaign.

## From verdicts to the next campaign

`planning.py` turns the verdicts into a sampling plan (the **Evidence gap** page,
`/plan` in the API, `outputs/campaign_plan.csv`).

- **Sites to re-sample.** Every site named by the ARG headline (high ARG, missed by the
  composite), the within-city hotspots, the composite contradictions and the unexplained
  high-risk sites, counted once and listed with each insight it tests. 31 sites, 5 of
  which test two insights.
- **Data needed to change a verdict.** Sample sizes use the Fisher z-transform with the
  Fieller variance factor for Spearman's ρ, var(z) ≈ 1.06 / (n − 3), at 80% power.
  - ARG headline: about 410 sites for the 95% interval to shrink to ±0.10.
  - Exploratory signals: the network size at which today's within-city ρ would clear
    the same family-wise bar (|ρ| ≥ 0.32 at n = 96, held fixed in z units): 260 to 505 sites.
  - Rejected signals: over 4,000 sites. No realistic campaign revives them.
  - City differences and model transfer need a new design (another season, a sixth
    city), not more sites.

These are planning estimates at the current spread of conditions, not guarantees.

## Limits of the engine itself

- One sample per site, and each city was sampled in a single campaign (May, June–July
  or September). City and season
  cannot be separated.
- A null result on 96 sites cannot rule out a small ARG–faecal link (|ρ| below about 0.22).
- Inside cities, ARG is weakly related to pathogen risk (ρ = +0.22, p = 0.033). The
  engine reports this next to the headline.
- The thresholds (0.15, 0.10, 0.35, 1.5 SD) are choices, stated here and in the code.
