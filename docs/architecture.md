# Architecture

```mermaid
flowchart LR
    subgraph Sources
        A[OneAquaHealth Resilience Map API<br/>api.enora-oah.eu] 
        U[Citizen submissions]
    end

    A -->|fetch CSVs| I[Ingest<br/>scripts/fetch]
    U --> V

    I --> J[Join layer<br/>data.build_analysis_table<br/>1 row / site]
    J --> V[Quality & validation<br/>quality.validate_submissions<br/>swap · dup · junk · region]
    V --> F[Feature store<br/>features.build_feature_matrix<br/>log-distances + buffers]
    F --> M[Model + uncertainty<br/>elastic-net · LOCO CV · conformal]
    M --> E[Explanation<br/>explain.site_contributions]

    J --> API[Interoperability API<br/>SensorThings · GeoJSON · FHIR]
    M --> API

    E --> D[Dashboard<br/>Streamlit]
    M --> D
    V --> D
    M --> S[Scenario / early-warning<br/>simulator + alert rules]
    S --> D
    V --> C[Citizen copilot<br/>validate → estimate → action]
    E --> C
    C --> D

    API --> EXT[External systems<br/>public-health / GIS]
```

## Flow in words
1. **Ingest** the eight source tables from the public Resilience Map API.
2. **Join** everything to one row per site on the site code.
3. **Validate** citizen submissions with deterministic, explainable rules.
4. **Feature store** builds log-distances and keeps collinear buffer families.
5. **Model + uncertainty**: elastic-net per component, leave-one-city-out validation,
   split-conformal intervals.
6. **Explanation** turns coefficients into plain-language drivers.
7. **Serve** three ways: a Streamlit dashboard (map, health card, drivers, scenario,
   copilot, data-quality), a standards-aligned **API** (SensorThings/GeoJSON/FHIR),
   and an **alert feed** from the scenario engine.

## Real-time path (design, for when time-series arrives)
Replace the batch ingest with a **SensorThings ingestion** of sensor/lab feeds; the
same join → feature → model → alert chain runs incrementally, and the scenario
thresholds become live triggers. The current data is cross-sectional, so this path
is architected but not yet fed.
