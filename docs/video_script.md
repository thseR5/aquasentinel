# Demo video script

Target 4:40, hard cap 5:00. One story: the ARG finding, how it was challenged, and what to collect next. Read the **Say** column while doing the **Do** column.
Every number below is produced by the app from the data.

## Before recording
1. Open the live app and wait until the insight feed shows the two charts.
2. Open a second tab on the API: run `make api` and load
   `http://localhost:8000/plan`. Skip that shot if you do not run the API.
3. Close notifications. Use full screen at 1080p. Turn captions on when you upload.
4. Pause for one second between sections so cuts are easy.

## Script

| Time | Do | Say |
|---|---|---|
| 0:00–0:15 | Insight feed, top of page. | "A single score can hide an important environmental risk. OneAquaHealth rates 96 stream sites in five European cities on pathogen, faecal and antibiotic-resistance risk, and averages them into one composite score." |
| 0:15–0:50 | Headline panel, rank chart. Hover a blue dot top right, then T10. | "Here every site is placed by its composite rank and its antibiotic-resistance rank. The blue dots are in the top 24 for ARG but outside the top 24 composite. That is 18 of 24. This one, T10 in Toulouse, has an ARG value of 0.64 and a composite of 0.23. An inspection plan built on the composite would never visit it." |
| 0:50–1:20 | Scroll to the two correlation charts. Hover a dot in each. | "Why? Pathogen risk follows faecal risk: 0.72, positive in all five cities. ARG against faecal: minus 0.03. In this data there is no detectable association between them, so averaging them buries ARG." |
| 1:20–1:50 | Open "How this was challenged" on the headline card. | "Before showing that, AquaSentinel tried to break it. A bootstrap interval from minus 0.22 to plus 0.17, spanning zero. The same test with the city effect removed: still about zero. And it reports what it cannot claim: inside cities ARG is weakly linked to pathogen risk, so the claim is 'not explained by faecal risk', not 'independent of everything'." |
| 1:50–2:30 | Scroll to **False leads stopped**. Open *distance to crop fields*. Point at the False leads tile (6). | "Every pattern goes through the same challenge. Distance to crop fields looks like a risk signal: minus 0.22 across all sites. Inside cities it is minus 0.06. It was a difference between cities, so it is rejected. Six patterns were stopped like this before they could reach a decision: three rejected, three downgraded because we screened 59 features and the best of 59 looks this strong by chance." |
| 2:30–3:10 | Evidence gap page. Point at the table, the chart, then "31". | "So what would change our mind? AquaSentinel says it. About 410 sites would pin the ARG result to within 0.1. A few hundred would settle the landscape hypotheses. The rejected ones would need more than 4,000, so they are closed. And here is where to collect: 31 sites, each listed with the insights it would test. The plan downloads as a CSV." |
| 3:10–3:50 | Tools → Citizen site check. Check with the default values, then 50.81345 / 3.77993. | "Citizen data has to earn its place too. This real entry has latitude and longitude swapped: caught, with the fix, and the lab results from the site 500 metres away. This one is already registered six times, so the advice is to add a visit. No sample, no risk score: nothing is estimated for a stream that has not been sampled." |
| 3:50–4:10 | Citizen data quality tiles; then switch language to Português. | "Across 71 registrations, 30 need fixing, and the cleaned registry of 47 sites downloads in one click. The interface also runs in Portuguese." |
| 4:10–4:25 | API tab: `/plan`, then `/fhir/Observation/C5`. | "Everything is available to other systems: OGC SensorThings, GeoJSON, an HL7 FHIR observation, and the evidence-gap plan itself." |
| 4:25–4:40 | Back to the insight feed. | "Discover, challenge, decide, collect. AquaSentinel: evidence before action. Don't just ask what the data says; ask whether it has earned the right to say it." |

## Pre-flight checklist
- [ ] Insight feed shows Supported 7, Exploratory 4, False leads stopped 6, the rank chart with 18 blue dots, and both correlation charts.
- [ ] Evidence gap shows 31 sites, 5 testing two insights, and sites needed 408 / 505 / 293 / 260.
- [ ] Priority lens on ARG shows "18 / 24" and T10 with ARG 0.64, composite 0.23.
- [ ] Exploratory card for vegetation fragmentation shows family-wise p = 0.90.
- [ ] Rejected card for crop fields shows −0.22 overall and −0.06 inside cities.
- [ ] Citizen site check, default values (Zwalm, 3.71, 50.88): swap warning with the fix
      50.88, 3.71, and lab results for G10, 0.5 km away.
- [ ] Citizen site check, 50.81345 / 3.77993: "already registered as Zwalm upstream ww -group2".
- [ ] Data quality tiles: 71, 30, 10, 3, 19, 47.
- [ ] Map shows the site dots (it needs an internet connection for the map tiles).
- [ ] Video is under 5 minutes.

## After recording
Upload to YouTube (unlisted is fine) and put the link in the Devpost form and in
`docs/devpost.md` under Links.
