# Data dictionary

All data derives from the **OneAquaHealth Resilience Map public API**
(`https://api.enora-oah.eu/api`) and is a **cross-sectional snapshot**
(one sample per site, May–Sep 2023; one 2024 sample for BN14).

## `sites.csv` — 106 monitoring sites
| column | meaning |
|---|---|
| `code` | research site code (e.g. `C5`, `BN2`); primary key |
| `name` | site name |
| `city_id`, `city_name` | partner city (Coimbra CO, Toulouse TO, Ghent GH, Benevento BE, Oslo OS) |
| `latitude`, `longitude`, `altitude` | WGS84 coordinates, metres |

## `health_risks.csv` — 96 sites (the modelling targets)
| column | meaning |
|---|---|
| `researchSiteCode` | join key |
| `samplingDate` | date of the sample |
| `scaledPathogenRisk` | 0–1 scaled pathogen-presence risk |
| `scaledFecalRisk` | 0–1 scaled faecal-indicator risk |
| `scaledArgRisk` | 0–1 scaled antibiotic-resistance-gene (ARG) risk |
| `healthRiskScore` | **composite = mean of the three components** (verified, max error 7e-5) |

We model the **three components** as the real targets; the composite is derived.

## `health_timeseries.csv` — long format of the same risk values
One date per site per metric. **Not a real time series** — do not use for temporal
forecasting.

## `nitrates.csv` — one nitrate value per site
| column | meaning |
|---|---|
| `siteCode`, `date` | join key, date |
| `statusOfNitrate` | nitrate concentration, mg/L (range 0.001–8.68; Toulouse highest, mean ~2.7) |

## `urban_parameters.csv` — 104 sites, ~55 landscape features
Distances (metres, log-transformed for modelling): `distChampCulture` (crop fields),
`distanceToHospitals`, `distanceToLivingStreetRoad`, `distanceToMotorwayRoad`,
`distanceToSewageStations`.
Buffer families at 8 radii (50, 100, 250, 500, 750, 1000, 1500, 2000 m):
`imperviousPct{r}m`, `urbanPct{r}m`, `vegCoverFrac{r}m`, `patchDensityVeg{r}m`,
`patchDensity{r}m`, `humanDensityProxy{r}m`. Buffer families are highly collinear
across radii (handled with elastic-net L2 grouping).

## `weather_summary.csv` — 106 sites
Long-run climate summary per site: `min/mean/maxTemperatureC`,
`min/mean/maxPrecipitationMm`. **Station-level context**, shared by many sites —
not daily weather.

## `user_generated_sites.csv` — 71 citizen submissions
| column | meaning |
|---|---|
| `userSiteCode`, `name` | id and free-text name |
| `latitude`, `longitude`, `altitude` | citizen-entered coordinates |

Contains real quality problems: test/junk names (`test`, `fgdgh`, `Random`,
`This site`), swapped lat/long (e.g. `Zwalm` at 3.71, 50.88), near-duplicate
points (many `Site 3` within metres in the Zwalm), and points far outside the
partner countries. The quality validator flags all of these.

## Derived analysis table (`build_analysis_table`)
Left-join of every source onto `sites` on the site code → one row per site with
targets, nitrate, landscape features and climate context. Missing joins stay NaN.
