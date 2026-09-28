# Judging-criteria map

How each feature serves the five official criteria (weights from the hackathon rules).

| Feature | Impact & Alignment (30%) | Innovation (20%) | Technical (20%) | UX (15%) | Scalability (15%) |
|---|:--:|:--:|:--:|:--:|:--:|
| **Data-quality validator** (79% of citizen entries triaged) | ● One Health data trust | ● explainable, deterministic rules | ● unit-tested | ● officer triage view | ● O(n) rules, any city |
| **Risk map** (106 sites, 5 cities) | ● prioritises inspection | | ● GeoJSON layers | ● colour-blind-safe | ● add city = drop coords |
| **Site health card** (observed + drivers + uncertainty) | ● actionable per site | ● plain-language SHAP-style drivers | ● conformal intervals | ● jargon glossary, EN/PT | |
| **Drivers & model page** (LOCO validation, honesty box) | ● credible to researchers | ● shows what data *can't* do | ● LOCO vs baseline, GBM check | ● transparent | |
| **Scenario / early-warning simulator** (alerts) | ● early-warning for officers | ● what-if engine on weak-signal data, honest intervals | ● live prediction + thresholds | ● sliders, instant | ● design for real-time SensorThings |
| **Citizen copilot** (validate → estimate → action) | ● closes the loop to citizens | ● LLM guardrail: explains only validated data | ● reuse nearest-site features | ● 3-step flow | ● stateless |
| **Interoperability API** (SensorThings/GeoJSON/FHIR) | ● environment↔public-health link | ● FHIR mapping of environmental risk | ● FastAPI, OpenAPI docs | | ● standards = plug-in |
| **i18n + accessibility** (EN/PT, WCAG-aware palette) | ● reaches partner communities | | | ● keyboard, contrast | ● add language = dict |

## Headline impact numbers (all computed from the data)
- **Ranks 106 sites in 5 cities** so inspection effort goes to the top 10% first
  (top: C5 0.78, BN2 0.73, BN10, C6, C12).
- **Auto-triages 79% (56/71) of citizen submissions** needing review: 10 junk names,
  19 duplicates, 1 coordinate swap, 30 out-of-region — freeing researcher time.
- **Honest model envelope:** weak pathogen rank signal (LOCO ρ=0.40); no target beats
  baseline on MAE → we scope the model to screening, not prediction.
