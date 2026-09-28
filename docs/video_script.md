# Demo video script (target 4:40, hard cap 5:00)

Record at 1080p, screen + voiceover. Have the app running locally with the model
artifact built (`make analyze`). Keep the mouse deliberate; pause on numbers.

| Time | Screen | Voiceover |
|---|---|---|
| **0:00–0:30** — Hook | Risk map, zoom to **C5 (Coimbra)** glowing red | "This stream site in Coimbra scores 0.78 on our health-risk index — near the top of 106 sites across five European cities. AquaSentinel finds it in seconds, and tells you *why* and *what to do* — honestly." |
| **0:30–1:00** — Problem | Split: noisy `user_generated_sites.csv` rows; a plain lab table | "OneAquaHealth has great data, but officers can't see which sites are risky, citizen entries are noisy, and there's no early-warning view. That's a One Health blind spot." |
| **1:00–1:45** — Live map | Toggle layers (pathogen → faecal → ARG → nitrate); click C5 popup | "Every site, coloured by observed risk. Switch between pathogen, faecal, antibiotic-resistance and nitrate. Colour-blind-safe, five cities, one view." |
| **1:45–2:30** — Health card | Open **C5** health card | "The three risk components, nitrate against an indicative EU reference, and where C5 sits — higher than 95% of Coimbra. Plain-language drivers: dense landscape fragmentation, closeness to wastewater. And an honest uncertainty band." |
| **2:30–3:15** — Scenario / alert | Scenario page on C5; raise impervious +30%, drop vegetation −30% | "This is our early-warning engine. Push impervious surface up, vegetation down — the estimate shifts and crosses Coimbra's 80th-percentile threshold, firing an alert an officer would act on. Note the wide interval — we show direction, not false precision." |
| **3:15–3:50** — Citizen copilot catches bad data | Copilot; enter name `Zwalm`, lat `3.71`, lon `50.88` | "A citizen submits a site — but the coordinates are swapped. AquaSentinel catches it instantly and suggests the fix: lat 50.88, lon 3.71. Then it finds the nearest monitored site, returns a screening band, and suggests next actions. The assistant only explains validated data — it never makes numbers up." |
| **3:50–4:20** — Interoperability + architecture | Browser: `/fhir/Observation/C5`; then the architecture diagram | "The same data, standards-ready: OGC SensorThings, GeoJSON, and an HL7 FHIR Observation — environmental risk in the language public-health systems already read. Ingest, validate, model, serve." |
| **4:20–4:40** — Honesty + close | Drivers & model page (LOCO table, red honesty box) | "And here's why judges can trust us: leave-one-city-out, no model beats a city-mean baseline on error. We say so, and scope the tool to screening and explanation. AquaSentinel — healthy waters, healthy communities, honestly." |

## Shot checklist
- [ ] Model built so drivers & predictions load.
- [ ] Zwalm swap demo returns the suggested fix.
- [ ] Scenario slider actually crosses the threshold (use C5 + impervious +30 / veg −30).
- [ ] FHIR endpoint open in a second tab beforehand.
- [ ] Captions on for accessibility.
