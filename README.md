# AquaSentinel

**Evidence Before Action — an evidence-first environmental intelligence engine for urban streams.**
*Healthy waters, healthy ecosystems, healthy communities.*

> AquaSentinel **discovers patterns, outliers and risk fingerprints** across citizen
> and environmental data, **challenges** each finding for statistical robustness
> (including city confounding), and presents **only what survives** — with the
> evidence behind it. **No evidence, no insight.**

Built for the **OneAquaHealth IEEE Global Hackathon 2026**.
**Primary track:** Data-to-Insight. **Secondary:** AI-Supported Assessment,
Digital Health Standards, Resilience Informatics.

---

## Why this exists
OneAquaHealth monitors urban streams across five European cities (Coimbra, Toulouse,
Ghent, Benevento, Oslo). The data is rich but messy, cross-sectional and confounded
by city. Most tools give you *another dashboard*. AquaSentinel instead **finds what
the data is actually saying and tells you whether it's worth believing** — the
question a researcher really has.

## What it does
1. **Insight Discovery Engine** — automatically searches the network for patterns,
   associations, contradictions, outliers, cross-city differences and coverage gaps.
   **12 insights discovered, 8 survive the challenge.** It even flags high-risk sites
   the trusted patterns *cannot* explain (e.g. BN15, 11.7 km from any wastewater
   station) as investigation candidates.
2. **"Challenge this insight"** — each finding is re-tested by removing city structure
   (within-city analysis) and a permutation test. Confounded findings are *rejected*:
   e.g. "distance to crop fields" (global ρ=−0.22) **collapses to ρ=−0.06 within city**
   and is marked weakened. The engine disproves its own weak claims.
3. **Evidence Cards** — every insight shows the statistic, sample size, geographic
   scope, an evidence-strength profile (observed / association / prediction / causal),
   what it *cannot* conclude, and the suggested next investigation.
4. **Risk fingerprints** — sites clustered by their observed pathogen / faecal / ARG
   profile (2 distinct profiles, permutation p=0.010); a single composite score blurs
   these together.
5. **Data-quality validator** — deterministic rules flag junk names, swapped
   coordinates, duplicates and out-of-region points. **Flags 79% (56/71)** of real
   citizen submissions needing review.
6. **Risk map + site health cards** — 106 sites, observed risk components, nitrate vs
   an indicative EU reference, percentiles, plain-language drivers, uncertainty.
7. **Association & prioritisation model** (supporting) — elastic-net with
   **leave-one-city-out** validation; honestly reported to *not* beat a city-mean
   baseline, so it is scoped to explanation and screening, never prediction.
8. **Scenario tool + citizen copilot** — what-if exploration with wide intervals, and a
   citizen reporter that validates a submission and explains only validated data.
9. **Interoperability API** — OGC SensorThings-shaped JSON, GeoJSON, and an **HL7 FHIR
   Observation** mapping (environment ↔ public health).
10. **Accessibility & i18n** — English + Portuguese, jargon glossary, colour-blind-safe.

## Honest headline
On **leave-one-city-out** cross-validation, **no model (elastic-net or gradient
boosting) beats a city-mean baseline on absolute error.** Only pathogen/composite
show a weak positive *rank* signal (LOCO Spearman 0.40 / 0.28); faecal and ARG go
negative. So the model is scoped to **explanation, coarse prioritisation and scenario
direction with wide intervals** — never precise prediction, never "safe to swim."
See [`docs/model_card.md`](docs/model_card.md).

## Quickstart
```bash
pip install -r requirements.txt      # or: make install

python scripts/fetch_data.py         # (optional) re-download raw CSVs from the public API
make profile                         # Step 1: profile + join coverage + data-quality report
make analyze                         # Step 2: analysis, LOCO CV, fit model, figures
make test                            # unit tests (19)

make app                             # launch the dashboard  -> http://localhost:8501
make api                             # launch the API        -> http://localhost:8000/docs
```
One command to rebuild everything and open the app: `make run`.
Docker: `docker build -t aquasentinel . && docker run -p 8501:8501 aquasentinel`.

## Live demo
Deployable free on Streamlit Community Cloud / Hugging Face Spaces (app) and
Render (API). Point the platform at `app/app.py`.

## Results (all computed from the data — see `outputs/`)
- **Top-risk sites:** C5 (0.78), BN2 (0.73), BN10, C6, C12.
- **Composite = mean of 3 components** verified (max error 7e-5).
- **Associations:** vegetation fragmentation @250 m ρ=+0.28 (p=0.006); distance to
  wastewater ρ=−0.22 (p=0.028).
- **Citizen triage:** 10 junk names, 19 duplicates, 1 coordinate swap, 30 out-of-region.

## Architecture
Ingest → join → validate → feature store → model + uncertainty → API + dashboard +
alerts. Diagram and real-time design in [`docs/architecture.md`](docs/architecture.md).

## Repo layout
```
aquasentinel/
├── app/app.py                 # Streamlit dashboard (8 sections)
├── api/main.py                # FastAPI: SensorThings / GeoJSON / FHIR
├── src/aquasentinel/          # data, quality, features, model, explain, i18n
├── scripts/                   # fetch_data, run_profile, run_analysis, compare_models
├── tests/                     # pytest (quality validator + pipeline)
├── data/raw/                  # 8 source CSVs
├── outputs/                   # figures, cv_results.json, model.joblib, reports
└── docs/                      # model_card, data_dictionary, architecture,
                               # devpost, video_script, judging_map, self_review
```

## Documentation
- [Model card](docs/model_card.md) · [Data dictionary](docs/data_dictionary.md)
- [Architecture](docs/architecture.md) · [Judging-criteria map](docs/judging_map.md)
- [Devpost write-up](docs/devpost.md) · [Demo video script](docs/video_script.md)
- [Skeptical self-review](docs/self_review.md)

## Data & credit
Data derives from the **OneAquaHealth** project (EU-funded) via its public Resilience
Map API. Data rights remain with OneAquaHealth and its partners. Code is MIT-licensed
(see [LICENSE](LICENSE)). This is a hackathon prototype for screening and
prioritisation — **not** a medical or regulatory tool.

## Ethics & safety
Environmental screening only; no personal data. Outputs are relative risk indices,
never diagnoses or "safe to swim" advice. Model limits are stated openly.
