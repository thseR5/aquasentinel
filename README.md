# 💧 AquaSentinel

**A One Health early-warning & insight platform for urban streams.**
*Healthy waters, healthy ecosystems, healthy communities.*

> AquaSentinel tells a city **which stream sites are a health risk, why, and what a
> citizen or officer should do next — and it tells you honestly how sure it is.**

Built for the **OneAquaHealth IEEE Global Hackathon 2026**.
**Primary track:** Resilience Informatics. **Secondary:** Data-to-Insight,
AI-Supported Assessment, Digital Health Standards.

---

## Why this exists
OneAquaHealth monitors urban streams across five European cities (Coimbra, Toulouse,
Ghent, Benevento, Oslo). The data is rich but hard to act on: officers can't see
which sites are risky and why, citizen submissions are noisy, and there's no
early-warning view. AquaSentinel closes those gaps — and does it with **scientific
honesty**, because the judges are researchers.

## What it does
1. **Data-quality validator** — deterministic, explainable rules flag junk names,
   swapped coordinates, duplicates and out-of-region points. **Catches 79% (56/71)**
   of the real citizen submissions needing review.
2. **Risk map** — 106 sites across 5 cities, coloured by observed pathogen / faecal /
   ARG / nitrate risk, colour-blind-safe.
3. **Site health card** — the three risk components, nitrate vs an indicative EU
   reference, city/EU percentile, plain-language drivers, and an uncertainty interval.
4. **Drivers & model page** — Spearman associations + **leave-one-city-out** validation
   against a baseline, with an honest "what the data can and can't tell us" box.
5. **Scenario / early-warning simulator** — move impervious cover, vegetation, distance
   to sewage, rainfall → see the risk shift and fire a mock officer alert when it
   crosses the city's 80th percentile.
6. **Citizen copilot** — submit a site → validate → estimate a screening band from the
   nearest monitored site → explain → suggest actions. The assistant only explains
   validated data and model output; it never invents numbers.
7. **Interoperability API** — the same data as OGC SensorThings-shaped JSON, GeoJSON,
   and an **HL7 FHIR Observation** mapping (environment ↔ public health).
8. **Accessibility & i18n** — English + Portuguese, jargon glossary, WCAG-aware palette.

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
