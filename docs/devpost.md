# AquaSentinel — Devpost write-up (paste-ready)

## Tagline
Evidence Before Action: discover, challenge, decide, collect. Stream-health insights that are tested before they are shown, and a plan for the evidence still missing.

## Track alignment
**Primary track: Data-to-Insight.** The challenge is that stream data "lacks clear
patterns, risks, or health indicators". AquaSentinel finds the patterns in the
OneAquaHealth data, tests each one, and says which can be acted on.

It also addresses two other tracks:
- **AI-Supported Assessment** — explainable, rule-based checks that catch swapped
  coordinates, duplicate registrations and test entries in citizen data.
- **Digital Health Standards** — the same data served as OGC SensorThings-shaped JSON,
  GeoJSON and an HL7 FHIR Observation mapping.

## The problem
OneAquaHealth has lab risk indicators for 96 stream sites in five European cities,
landscape context for each site, and 71 sites registered by citizens. Three things stand
between that data and a decision:

1. **One composite score per site.** It is the mean of pathogen, faecal and
   antibiotic-resistance risk. Nobody has checked whether those three move together.
2. **Patterns that may not be real.** With 59 landscape features and 96 sites, some
   correlations will look significant by chance, and the five cities differ so much that
   a pattern between cities can pass for a pattern between sites.
3. **Citizen data that cannot be used as it is.** Test entries, swapped coordinates and
   the same place registered six times.

## What we built
AquaSentinel searches the data for patterns, then tries to disprove each one. Every
insight gets a verdict: **supported**, **exploratory** (a hypothesis) or **rejected**.

- **Insight feed.** 14 insights as evidence cards: the statistic, the sample size, what
  cannot be concluded, the next step, and how the insight was challenged.
- **Priority lens.** The top quarter of sites on any risk dimension, from observed
  lab values, downloadable as CSV.
- **Evidence gap.** Every verdict turned into a plan: 31 sites to re-sample, each with
  the insights it tests, and for each insight how many sites would change the verdict.
- **Observed risk profiles** and a **risk map** of the five cities.
- **Citizen site check.** The checks an app should run at the moment of entry.
- **Citizen data quality.** Every flag with its suggested fix, and a cleaned registry to download.
- **Interoperability API** and an English/Portuguese interface.

## What it found
**ARG risk behaves differently from faecal risk, and a composite score can miss high-ARG sites.**

- Pathogen and faecal risk move together (ρ = +0.72, positive in all five cities).
- No detectable association between ARG and faecal risk (ρ = −0.03, 95% CI −0.22 to +0.17).
- The composite top quarter leaves out **18 of the 24 highest-ARG sites**.
- On the composite, the five cities look alike (p = 0.060). Split by component they
  differ, in opposite directions: Coimbra is highest for pathogen, Oslo for ARG.

Antimicrobial resistance is a core One Health concern, and faecal indicators are the
usual proxy for water-borne health risk. In this network the proxy does not track ARG.

The engine also turned down its own weaker findings:
- Three landscape associations pass the city check but not the correction for screening
  59 features. They are labelled exploratory.
- Three more disappear inside cities (distance to crop fields: ρ = −0.22 overall, −0.06
  inside cities). They are rejected.
- Landscape features do not predict risk in a city the model has not seen. The model
  beats a "predict the average" baseline for 0 of 4 targets.

## Target users
- **Researchers and OneAquaHealth partners** — which patterns are worth a follow-up
  campaign, and which were chance or city effects.
- **Municipal water and health officers** — which sites to sample again first, on which
  risk dimension.
- **Citizen scientists and app developers** — cleaner registrations at the moment of entry.

## Impact
- Gives officers an ARG watchlist of 24 sites, 18 of which a composite-led list would
  not contain.
- Turns 71 citizen registrations into 47 usable sites: 10 test entries dropped, 3 swapped
  coordinates corrected, 19 duplicates merged into 5 places. 34 of those sites are outside
  the five partner cities and are kept, not flagged.
- Gives OneAquaHealth a 31-site re-sampling campaign that tests four insights at once, and
  says up front which questions a campaign can settle (about 260 to 505 sites for the
  exploratory signals) and which it cannot (over 4,000 sites for the rejected ones).
- Stops effort being spent on six landscape "drivers" that are not supported by the data.

## How we built it
Python, pandas, SciPy and scikit-learn for the engine (Spearman with bootstrap intervals,
within-city re-tests, a family-wise permutation test, k-means against a simulated null,
Kruskal–Wallis with Holm correction, leave-one-city-out validation). Streamlit and Altair
for the app, Folium for the map, FastAPI for the API. 45 unit tests cover the engine, the
validator, the model validation, the API and the translations.

## What we changed our minds about
The first version had a scenario simulator and a risk estimate for unsampled citizen
sites. Both depended on the landscape model. When leave-one-city-out validation showed
the model does not beat a baseline, we removed both features. Applying the product's own
rule to the product was the most useful decision of the project.

## Limits
- One lab sample per site, and each city sampled in a single campaign. City and season
  cannot be separated, and nothing here is a forecast.
- 96 sites cannot rule out a small ARG–faecal link (|ρ| below about 0.22). Inside
  cities, ARG is weakly related to pathogen risk (ρ = +0.22).
- Risk values are relative 0 to 1 indices defined by OneAquaHealth, not probabilities of harm.
- Screening and prioritisation only. Not a diagnosis and not a "safe to swim" judgement.

## What's next
- Re-sample the high-ARG, low-faecal sites to confirm the headline with repeat data.
- Test the three exploratory landscape candidates on a new city or a new season.
- Move the entry-time checks into the OneAquaHealth citizen app.
- Ingest repeated samples through the SensorThings path so trends can be tested the same way.
- Add French, Italian, Dutch and Norwegian.

## Links
- Live app: <ADD YOUR STREAMLIT URL>
- Demo video: <ADD YOUR VIDEO URL>
- Source code: https://github.com/thseR5/aquasentinel
