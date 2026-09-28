# Skeptical self-review (Step 5)

Reviewing AquaSentinel as a hostile judge would. Three weakest points, each either
fixed or openly acknowledged.

## Weakness 1 — "Your model doesn't work."
**The critique:** On leave-one-city-out, no model beats a city-mean baseline on MAE;
faecal and ARG rank correlations are *negative*. So why is there a model at all?

**Response (acknowledged + reframed, not hidden):** This is true and we lead with it
on the Drivers & model page and in the model card. Our claim was never "we predict
risk." The model earns its place three ways: (1) it produces the **plain-language
driver explanations** on every health card and in the copilot; (2) it gives a **weak
but positive pathogen/composite rank signal** (LOCO ρ=0.40 / 0.28) usable for *coarse*
prioritisation where no lab data exists; (3) it powers the **scenario direction** with
honest wide intervals. Health cards lead with **observed** values, not predictions. A
submission that faked strong metrics on n=96 cross-sectional data would be less
credible to a researcher, not more. **This honesty is the differentiator.**

## Weakness 2 — "Your risk targets and references are black boxes."
**The critique:** `scaledPathogenRisk` etc. are 0–1 indices with no stated derivation,
and the nitrate "EU reference" could mislead.

**Response (partially fixed, partially acknowledged):** We verified and documented the
one thing we *can* prove — the composite is exactly the mean of the three components
(max error 7e-5) — and we treat the components, not the composite, as targets. We label
the scaled risks as **relative indices, not calibrated probabilities of harm**, in the
model card and UI. The nitrate reference is shown as **indicative context with an
explicit caveat** that stream thresholds differ; we never render a pass/fail. Remaining
gap: the upstream scaling method is OneAquaHealth's, not ours — we link to their
Resilience Map rather than re-deriving it. Documented in the data dictionary.

## Weakness 3 — "Citizen validation and copilot could give harmful false confidence."
**The critique:** The swap detector misses swaps that stay out-of-region (e.g. some
Brazilian entries flagged only as out-of-region), and the copilot estimates a new
site's risk by borrowing the *nearest* monitored site — which could be misleading.

**Response (acknowledged + guardrailed):** The swap detector's scope (swaps landing in
a partner country) is stated in the model card, and out-of-region entries are still
flagged, so nothing silently passes. The copilot (1) only estimates when a monitored
site is **within 50 km**, else it refuses and just logs the observation; (2) shows the
**distance to that borrowed site** and a **wide uncertainty band**; (3) frames output
as a screening band with actions like "sample again in 2 weeks," never a safety verdict;
(4) the LLM/explanation layer only rephrases validated data and model coefficients — it
cannot introduce numbers. These guardrails are demonstrated in the video (the Zwalm
swap catch).

## Other known limitations (stated, not fixed in the time box)
- Cross-sectional data → no true temporal forecasting; the real-time path is designed,
  not fed.
- `weather_summary` is station-level context shared across many sites, so its features
  are coarse.
- i18n covers English + Portuguese; the other three partner languages are stubs.
- No formal WCAG audit yet (palette is colour-blind-safe and contrast-aware by design).

## Net assessment
The submission's strength is an **honest, reproducible pipeline** with a genuinely
useful **data-quality layer** and **interoperability**, wrapped in a UX that a
non-expert can use — not an oversold model. Every headline number regenerates with
`make analyze`.
