# Demo recording guide — one clean take

This is a teleprompter script: read the **Say** column aloud while doing the **Do**
column. Target 4:40; hard cap 5:00. All numbers are real (verified from the data).

## Before you record (5 minutes of setup)
1. **Open the live app** in a browser and reload until the map shows dots across
   Europe (confirms the deploy is current). Keep this tab open.
2. **Open a second tab** to the API FHIR endpoint you'll show at the end — either
   your Render URL `/fhir/Observation/C5`, or if the API isn't deployed, run it
   locally first (`uvicorn api.main:app --port 8000`) and open
   `http://localhost:8000/fhir/Observation/C5`. Skip this shot if you didn't deploy
   the API.
3. **Open the architecture diagram**: the file `docs/architecture.md` on GitHub
   renders the Mermaid diagram — open that page in a third tab.
4. Close notifications, silence your phone, set the browser to full screen.

## Recording tool (Mac, built in — no install)
- Press **Cmd + Shift + 5** → choose **Record Entire Screen** (or Selected Portion
  around the browser) → **Options** → set **Microphone** to your mic → **Record**.
- Speak clearly; pause 1 second between sections so edits are easy.
- Stop with the same **Cmd + Shift + 5** or the menu-bar stop button. The file saves
  to the Desktop as a `.mov` — that is what you upload to Devpost.
- Optional: trim the start/end in QuickTime (open file → Edit → Trim).

## The script

| Time | Do (on screen) | Say (read aloud) |
|---|---|---|
| 0:00–0:20 | Start on the **Insight feed** (the landing page). Let the header "What did the data reveal?" and the Survived/Weakened counts show | "106 stream sites, 96 health observations, 71 citizen reports. Most tools would give you another dashboard. AquaSentinel asks a harder question: what can we actually learn from this data — and is it worth believing?" |
| 0:20–0:55 | Scroll the first surviving Evidence Card: **2 risk fingerprints**, then **vegetation fragmentation @250m** | "It searched the network and surfaced real patterns. Sites fall into two distinct risk fingerprints — a permutation test says that structure beats chance at p equals 0.01. And vegetation fragmentation tracks health risk: rho +0.28, and it holds inside every city." |
| 0:55–1:30 | Scroll to a **Weakened** card ("distance to crop fields"); open its **Challenge this insight** expander | "Here's the part I'm proud of. This association looks real — rho minus 0.22. But when we remove city structure and re-test, it collapses to minus 0.06. It was city confounding. AquaSentinel challenges its own findings and rejects the weak ones. No evidence, no insight." |
| 1:30–1:55 | Back on the feed, scroll to the **"high-risk sites the patterns can't explain"** card (BN15) | "It even flags where its own model is blind. This Benevento site is high-risk, but it's 11 kilometres from any wastewater station with no vegetation fragmentation — the trusted patterns predict low risk. So AquaSentinel marks it an investigation candidate: sample here first, because the environment doesn't explain it." |
| 1:55–2:15 | Go to **Risk fingerprints**; show the two profiles + scatter | "It also groups sites by the shape of their risk — pathogen-dominant versus ARG-dominant — which a single composite score would hide from an officer deciding what to inspect." |
| 2:00–2:30 | Go to Site health card, select **C5** | "Drill into any site. C5 in Coimbra: the three observed risk components, nitrate against an indicative European reference, its percentile, plain-language drivers, and an honest uncertainty band." |
| 2:30–3:15 | Go to Scenario simulator, base site **G4** (Ghent); set "Distance to sewage station" to **−50%** and "Peak rainfall" to **+50%** | "This is the early-warning engine. Move this Ghent site closer to a wastewater station and add heavy rainfall — the estimate rises from below Ghent's threshold to above it, firing an alert an officer would act on. The shift is deliberately modest, with a wide interval: we show direction, not false precision." |
| 3:15–3:50 | Citizen copilot. First enter "Zwalm", Latitude **3.71**, Longitude **50.88** → Validate & assess (shows the swap warning + suggested fix). Then correct it: Latitude **50.88**, Longitude **3.71** → Validate & assess again (now valid; nearest site G10 "Zwalm6", 0.5 km; returns a screening band + actions) | "A citizen submits a site — but the coordinates are swapped. AquaSentinel catches it and suggests the fix: latitude 50.88, longitude 3.71. Enter the corrected point and it validates, finds the nearest monitored site half a kilometre away — the real Zwalm station — and returns a screening band with next actions. The assistant only explains validated data; it never invents numbers." |
| 3:50–4:20 | Switch to the FHIR tab (`/fhir/Observation/C5`), then the architecture-diagram tab | "The same data is standards-ready: OGC SensorThings, GeoJSON, and an HL7 FHIR Observation — environmental risk expressed in the language public-health systems already read. The pipeline is ingest, validate, model, serve." |
| 4:20–4:40 | Go to Drivers and model section; scroll to the validation table and the honesty note | "And here's why this is credible. We validated with leave-one-city-out: no model beats a city-mean baseline on error, so we scope the tool to explanation, prioritisation and scenarios — and we say so. AquaSentinel: healthy waters, healthy communities, honestly." |

## Pre-flight checklist
- [ ] Insight feed loads and shows Survived (8) / Weakened (4) counts.
- [ ] A weakened card's "Challenge this insight" expander shows the within-city collapse.
- [ ] Live app map shows dots (deploy is current).
- [ ] Zwalm entry (lat 3.71, lon 50.88) returns the swap warning + suggested fix;
      the corrected entry (lat 50.88, lon 3.71) validates and finds G10 "Zwalm6".
- [ ] Scenario on **G4** with Distance to sewage −50% and Peak rainfall +50% crosses
      Ghent's threshold and fires the alert (base is just below, scenario just above).
- [ ] FHIR tab pre-loaded (or API running locally).
- [ ] Microphone selected in the Cmd+Shift+5 Options menu.
- [ ] Screen recording is full-screen, notifications off.

## After recording
- Trim dead air at the start/end in QuickTime.
- Upload the `.mov` to YouTube (unlisted) or directly to Devpost.
- Put the link in the Devpost submission alongside the live app URL and the GitHub
  repo. Keep it under 5 minutes.
