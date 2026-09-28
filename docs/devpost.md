# AquaSentinel — Devpost write-up

## Track alignment
**Primary track: Resilience Informatics** (early warning & resilience planning).
**Secondary strengths:** Data-to-Insight (dashboards, maps, One Health summaries),
AI-Supported Assessment (explainable citizen-data validation, human-in-the-loop),
and Digital Health Standards (SensorThings / GeoJSON / FHIR interoperability).

## The problem
Urban streams are a **One Health** pressure point — where environment, animal and
human health meet. OneAquaHealth collects rich data (lab risk indicators, landscape
context, citizen reports) across five European cities, but three gaps remain:
1. Officers can't quickly see **which sites are a health risk, and why**.
2. **Citizen submissions are noisy** — test entries, swapped coordinates, duplicates.
3. There's no **early-warning / what-if** view, and data is fragmented across formats.

## The solution
**AquaSentinel tells a city which stream sites are a health risk, why, and what a
citizen or officer should do next — and it tells you honestly how sure it is.**

- **Risk map** of 106 sites in 5 cities, coloured by observed pathogen/faecal/ARG/
  nitrate risk.
- **Site health cards**: the three risk components, nitrate vs an indicative EU
  reference, city/EU percentile, plain-language drivers, and an uncertainty interval.
- **Scenario / early-warning simulator**: move impervious cover, vegetation, distance
  to sewage, rainfall context → see the risk shift and fire a mock officer alert when
  it crosses the city's 80th percentile.
- **Citizen copilot**: submit a site → we validate coordinates & duplicates → estimate
  a screening risk band from the nearest monitored site → explain it → suggest next
  actions. The assistant only explains validated data and model output; it never
  invents numbers.
- **Data-quality triage**: deterministic, explainable rules that catch **79%** of the
  real citizen submissions needing review.
- **Interoperability API**: the same data as OGC SensorThings-shaped JSON, GeoJSON,
  and an **HL7 FHIR Observation** mapping that expresses environmental risk in the
  grammar public-health systems already read.

## Target users
- **Municipal water / health officers** — prioritise inspections, get alerts.
- **Researchers** — trust the pipeline; see validated citizen data and honest limits.
- **Citizen scientists** — contribute clean data and get an understandable result.

## Measurable impact (computed from the data)
- Ranks **106 sites across 5 cities** so inspection effort targets the top 10% first
  (C5, BN2, BN10, C6, C12).
- **Auto-triages 56/71 (79%)** citizen submissions: 10 junk names, 19 duplicates,
  1 coordinate swap, 30 out-of-region.
- Surfaces significant One Health associations (vegetation fragmentation ρ=+0.28;
  distance to wastewater ρ=−0.22).

## What makes it credible (and different)
We ran **leave-one-city-out** validation and report the uncomfortable truth: on
absolute error, **no model beats a city-mean baseline**, and only pathogen/composite
show a weak positive *rank* signal. So we scoped the model to explanation, coarse
prioritisation and scenario direction — with wide conformal intervals — instead of
overclaiming prediction. Researcher-judges can trust what we say because we say what
the data *can't* do.

## What's next
- Feed the **real-time SensorThings** path with live sensor/lab streams to turn the
  scenario engine into true temporal early warning.
- Auto-compute landscape features for any new point from OpenStreetMap / Copernicus
  imperviousness, so adding a city is a coordinate drop-in.
- City-level hierarchical model with partial pooling to improve transfer.
- Full WCAG audit and the remaining partner languages (FR, IT, NL, NO).

## Built with
Python, pandas, scikit-learn (elastic-net, conformal), SHAP-style coefficient
explanations, Streamlit, Folium, FastAPI (SensorThings/GeoJSON/FHIR), matplotlib.
Data via the OneAquaHealth Resilience Map public API.
