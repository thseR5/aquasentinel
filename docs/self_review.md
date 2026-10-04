# Self-review

AquaSentinel reviewed the way a sceptical judge would review it. The first part lists
what an earlier version got wrong and what was done about it. The second part lists the
weaknesses that remain.

## What the review changed

| Problem found | What we did |
|---|---|
| The engine picked the 6 strongest of 59 features and passed them at p < 0.10. Nothing corrected for the 59 tests. | Added a family-wise permutation test. No association clears it, so the three associations that had "survived" are now labelled **exploratory**. |
| The "risk fingerprints" were described as different risk shapes ("faecal-dominant" against "ARG-dominant"). In fact the two groups differ in the level of pathogen and faecal contamination; ARG is the same in both (0.37 and 0.35). | Relabelled them, and tested the real question directly. That produced the headline: ARG is independent of faecal risk. |
| The fingerprint test shuffled each column, which only proves the components are correlated. | Replaced the null with simulated data that keeps the correlations but has no clusters, and gave it the same choice of k. The profiles still pass (p = 0.015). |
| The model's "weak rank signal of 0.40" came from pooling predictions across cities. Inside held-out cities it averages +0.13 for pathogen and ranges from −0.37 to +0.64. | Rank agreement is now computed inside each held-out city. The baseline is named for what it is: the mean of the training cities. |
| A scenario simulator fired "alerts" on shifts of about 0.03 with an interval of about ±0.26, from a model with no demonstrated skill. Its rainfall slider moved a station-level climate value. | Removed. |
| The citizen tool estimated risk for a new site from a monitored site up to 50 km away. | Removed. The tool now shows observed lab results only when a monitored site is within 2 km, and says so when there is none. |
| "79% of citizen entries need review" counted 26 valid sites in Greece, Austria, Brazil and the United States as problems. | Being outside lab coverage is now a note, not a flag. The honest figure is 42% (30 of 71). |
| Only 1 of 3 swapped coordinates was caught. | Swap detection now uses nearby known points anywhere in the world. All 3 are caught, and a test covers the case where two lone points could each be the other's swap (neither is flagged). |
| The 80% interval was computed at the 90% quantile of absolute residuals. | Fixed, with the finite-sample correction. |
| Docs named two different primary tracks and described features that did not exist in the code. | One track (Data-to-Insight). Every claim in the docs maps to code or to a file in `outputs/`. |

## Weaknesses that remain

**1. The headline is a null result on 96 sites.**
"No association between faecal and ARG risk" is supported by a confidence interval of
−0.22 to +0.17. That rules out a strong link, not a small one. Inside cities, ARG is
weakly related to pathogen risk (ρ = +0.22, p = 0.033), which the feed reports next to
the headline. The practical claim does not depend on the null: 18 of the 24 highest-ARG
sites are absent from the composite top quarter, and that is a count of observed values.

**2. City and season are confounded.**
Ghent and Toulouse were sampled in May, Coimbra and Benevento in June and July, Oslo in
September. The cross-city differences could be seasonal. The card says so. Only repeated
sampling can separate them.

**3. One sample per site.**
Every site-level statement (hotspots, watchlist membership) describes one day. The
watchlist is framed as "where to sample again", not as a ranking of safety.

**4. We did not define the risk indices.**
The 0 to 1 pathogen, faecal and ARG values are scaled upstream by OneAquaHealth. We
verified that the composite is their mean, but not how each was scaled. If the ARG
index were scaled in a way that removed real variation, the headline would weaken.

**5. Thresholds are choices.**
0.15 and p < 0.10 for the city check, 1.5 SD for hotspots, 0.35 for the composite gap,
25 m for duplicates, 50 km for coverage. They are stated in the code and the docs, and
the conclusions do not sit on a knife edge (the family-wise p-values are 0.34 to 0.90,
nowhere near 0.05), but another analyst could choose differently.

**6. The validator's name rule is crude.**
It flags "S4" as a placeholder name, which may be a real site label, and it would miss
a test entry with a plausible name.

**7. Not yet built.**
Insight texts are in English only; the interface is in English and Portuguese. There
has been no formal accessibility audit. The API is a demonstration mapping, not a
certified SensorThings or FHIR server.

## Net assessment
The strongest parts are the ones that survive attack: a specific, checkable finding
about antibiotic resistance, a watchlist that follows from it, and a citizen-data
cleaner whose every flag can be explained. The weakest part was the predictive model,
and the product is better for having removed what depended on it.
