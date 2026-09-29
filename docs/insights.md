# Insight Discovery Engine

AquaSentinel's core is not a predictor — it is an engine that **discovers** candidate
insights, **challenges** them, and **publishes only what survives**, each with its
evidence. Rule enforced in code (`src/aquasentinel/insights.py`): **no evidence, no
insight** — every published finding carries a statistic, sample size and scope.

Reproduce: `make insights` (writes `outputs/insights.json`).

## The loop: DISCOVER → CHALLENGE → EXPLAIN → QUALIFY

### 1. Discover
- **Risk fingerprints** — KMeans on the observed pathogen/faecal/ARG profile; k chosen
  by silhouette.
- **Associations** — Spearman of each landscape/climate feature vs composite risk.
- **Contradictions** — sites where the composite score hides a dominant component.
- **Outliers** — sites far above their own city's norm (within-city z-score).
- **Cross-city differences** — Kruskal–Wallis across the five cities.
- **Citizen coverage** — deterministic data-quality triage of citizen submissions.

### 2. Challenge (the differentiator)
Each finding is actively attacked before it is trusted:
- **Associations** are recomputed **within city** (city mean removed from both
  variables) and checked for **sign consistency across cities**. A global association
  driven purely by between-city differences is flagged **weakened**.
- **Fingerprints** face a **permutation test**: the real silhouette is compared to
  silhouettes from data whose joint structure was destroyed by per-feature shuffling.
- **Cross-city** must clear p < 0.05.

### 3. Qualify — evidence strength
Every insight carries a four-part profile (0–4): **observed**, **association**,
**prediction**, **causal**. This makes the model's real limits explicit rather than
hidden: prediction and causal are low by design.

## What the engine found (from the real data)

| Insight | Evidence | Challenge outcome |
|---|---|---|
| 2 risk fingerprints | silhouette 0.38 | **Survives** — permutation p = 0.010 |
| Vegetation fragmentation @250 m ↔ risk | ρ = +0.28, p = 0.006, n = 96 | **Survives** — within-city ρ = +0.18, consistent 5/5 cities |
| Distance to wastewater ↔ risk | ρ = −0.22, p = 0.028 | **Survives** — within-city ρ = −0.23, p = 0.021, 4/5 cities |
| Composite hides a dominant dimension | arithmetic on components | **Survives** — robust by construction |
| Within-city outlier hotspots | within-city z ≥ 1.5 | **Survives** — descriptive |
| High-risk sites the patterns can't explain (e.g. BN15) | high risk + benign environment | **Survives** as an investigation flag (cause unknown) |
| 79% of citizen entries need review | 56/71 flagged | **Survives** — deterministic |
| Distance to crop fields ↔ risk | ρ = −0.22, p = 0.029 | **Weakened** — within-city ρ = −0.06 (city-confounded) |
| Distance to hospitals ↔ risk | ρ = −0.21, p = 0.038 | **Weakened** — within-city ρ = −0.06 |
| Cross-city risk difference | Kruskal H = 9.05 | **Weakened** — p = 0.060, not beyond chance |

The last three are the point: the engine **rejects its own weak findings**. A judge can
watch a plausible-looking association disappear once city structure is removed.

## Why this beats a dashboard
A dashboard shows numbers. AquaSentinel answers the harder question — *is this pattern
worth believing?* — which is exactly what turning messy citizen/environmental data into
**actionable, defensible** insight requires.
