"""Minimal i18n for the app: English + Portuguese (a partner language).

Copy is deliberately jargon-free; scientific terms are explained on first use.
Falls back to English for any missing key.
"""
from __future__ import annotations

LANGS = {"en": "English", "pt": "Português"}

_STR = {
    "nav": {"en": "Section", "pt": "Secção"},
    "overview": {"en": "Overview", "pt": "Visão geral"},
    "map": {"en": "Risk map", "pt": "Mapa de risco"},
    "health_card": {"en": "Site health card", "pt": "Ficha do local"},
    "drivers": {"en": "Drivers & model", "pt": "Fatores e modelo"},
    "scenario": {"en": "Scenario simulator", "pt": "Simulador de cenários"},
    "copilot": {"en": "Citizen copilot", "pt": "Copiloto cidadão"},
    "quality": {"en": "Data quality", "pt": "Qualidade dos dados"},
    "about": {"en": "About & export", "pt": "Sobre e exportação"},
    "disclaimer": {
        "en": "Screening & prioritisation only. Not a diagnosis or a 'safe to swim' judgement.",
        "pt": "Apenas triagem e priorização. Não é diagnóstico nem indicação de 'seguro para nadar'.",
    },
    "overview_title": {"en": "AquaSentinel — healthy waters, healthy communities",
                       "pt": "AquaSentinel — águas saudáveis, comunidades saudáveis"},
    "pitch": {
        "en": "**AquaSentinel tells a city which stream sites are a health risk, why, "
              "and what to do next — and it tells you honestly how sure it is.** "
              "It links stream lab data, citizen reports, landscape and climate context "
              "into one screening view under the One Health approach.",
        "pt": "**O AquaSentinel indica que locais de ribeiras representam risco para a saúde, "
              "porquê e o que fazer a seguir — e diz honestamente qual a certeza.**",
    },
    "cities": {"en": "Cities", "pt": "Cidades"},
    "sites": {"en": "Monitoring sites", "pt": "Locais monitorizados"},
    "with_labs": {"en": "Sites with lab risk data", "pt": "Locais com dados de risco"},
    "flagged_pct": {"en": "Citizen entries needing review", "pt": "Entradas a rever"},
    "honesty_banner": {
        "en": "Data is a cross-sectional snapshot (one sample per site, May–Sep 2023). "
              "AquaSentinel prioritises inspection effort and estimates risk where labs are "
              "missing — it does not forecast a time series.",
        "pt": "Os dados são um instantâneo transversal (uma amostra por local, mai–set 2023).",
    },
    "top_risk": {"en": "Highest observed health-risk sites", "pt": "Locais de maior risco observado"},
    "map_title": {"en": "Where is stream health risk concentrated?",
                  "pt": "Onde se concentra o risco?"},
    "layer": {"en": "Colour sites by", "pt": "Colorir por"},
    "map_caption": {
        "en": "Colours show observed values where lab data exists. Grey = no measurement.",
        "pt": "As cores mostram valores observados onde há dados. Cinza = sem medição.",
    },
    "card_title": {"en": "Site health card", "pt": "Ficha de saúde do local"},
    "select_site": {"en": "Choose a site", "pt": "Escolha um local"},
    "composite": {"en": "Composite risk", "pt": "Risco composto"},
    "percentile_line": {
        "en": "Higher than **{pc}%** of sites in {city} and **{pe}%** across all cities.",
        "pt": "Superior a **{pc}%** dos locais em {city} e **{pe}%** no total.",
    },
    "nitrate_line": {
        "en": "Nitrate: **{v} mg/L** (indicative EU drinking-water reference ≈ {ref} mg/L; "
              "stream thresholds differ — treat as context, not a limit).",
        "pt": "Nitrato: **{v} mg/L** (referência indicativa UE ≈ {ref} mg/L).",
    },
    "why": {"en": "Why this estimate — main landscape factors", "pt": "Porquê — principais fatores"},
    "no_drivers": {"en": "The model finds no strong landscape driver here; the estimate "
                         "sits near the local average.",
                   "pt": "O modelo não encontra fator forte; estimativa perto da média local."},
    "model_est_line": {
        "en": "Model screening estimate: {p} (80% interval {lo}–{hi}).",
        "pt": "Estimativa do modelo: {p} (intervalo 80% {lo}–{hi}).",
    },
    "card_honesty": {
        "en": "Bars above are **observed lab values**. The model estimate is a wide-interval "
              "screening aid; it is not validated to predict a new city (see Drivers & model).",
        "pt": "As barras são **valores observados**. A estimativa do modelo é auxiliar.",
    },
    "drivers_title": {"en": "What drives risk — and how well can we predict it?",
                      "pt": "O que impulsiona o risco?"},
    "associations": {"en": "Descriptive associations (Spearman, weak but significant)",
                     "pt": "Associações descritivas"},
    "validation": {"en": "Honest validation: leave-one-city-out vs baseline",
                   "pt": "Validação honesta"},
    "model_honesty": {
        "en": "Key finding: on leave-one-city-out cross-validation, neither elastic-net nor "
              "gradient boosting beats a city-mean baseline on error. Landscape features carry "
              "only a weak rank signal and do NOT reliably predict absolute risk in an unseen "
              "city. We report this rather than overclaim. The model is used for explanation, "
              "wide-interval screening, and scenario direction — not precise forecasting.",
        "pt": "Conclusão: na validação deixando-uma-cidade-de-fora, o modelo não supera a "
              "linha de base. Usamos o modelo para explicação e triagem, não previsão precisa.",
    },
    "scenario_title": {"en": "Scenario simulator (what-if)", "pt": "Simulador de cenários"},
    "scenario_caption": {
        "en": "Explore how the risk estimate shifts if landscape/climate context changes. "
              "Directional, with honest wide intervals — a design for real-time early warning "
              "once time-series data is connected.",
        "pt": "Explore como a estimativa muda se o contexto mudar.",
    },
    "base_site": {"en": "Base site", "pt": "Local base"},
    "adjust": {"en": "Adjust conditions:", "pt": "Ajustar condições:"},
    "base_risk": {"en": "Current estimate", "pt": "Estimativa atual"},
    "scenario_risk": {"en": "Scenario estimate", "pt": "Estimativa do cenário"},
    "alert_fire": {
        "en": "⚠️ ALERT: scenario risk exceeds the {city} 80th-percentile threshold ({thr}). "
              "A city officer would be notified to prioritise inspection.",
        "pt": "⚠️ ALERTA: risco do cenário acima do limiar de {city} ({thr}).",
    },
    "alert_ok": {"en": "No alert: scenario risk stays below the {city} 80th-percentile ({thr}).",
                 "pt": "Sem alerta: abaixo do limiar de {city} ({thr})."},
    "scenario_honesty": {
        "en": "Shifts follow the fitted (weak) associations and inherit wide uncertainty. "
              "Read as direction and relative size, not exact numbers.",
        "pt": "As variações seguem associações fracas; leia como direção, não valores exatos.",
    },
    "copilot_title": {"en": "Citizen copilot — submit a stream site",
                      "pt": "Copiloto cidadão — submeter um local"},
    "copilot_caption": {
        "en": "Validates your entry, finds the nearest monitored site, and returns a screening "
              "risk band with a plain explanation and next actions. The assistant only explains "
              "validated data and model output — it never invents numbers.",
        "pt": "Valida a entrada, encontra o local mais próximo e devolve uma faixa de risco.",
    },
    "site_name": {"en": "Site name", "pt": "Nome do local"},
    "check_btn": {"en": "Validate & assess", "pt": "Validar e avaliar"},
    "step1_validation": {"en": "1. Data-quality check", "pt": "1. Verificação de qualidade"},
    "validation_ok": {"en": "Entry looks valid.", "pt": "Entrada parece válida."},
    "validation_flags": {"en": "Flagged:", "pt": "Sinalizado:"},
    "swap_suggest": {"en": "Coordinates look swapped — did you mean lat {lat}, lon {lon}?",
                     "pt": "Coordenadas parecem trocadas — queria lat {lat}, lon {lon}?"},
    "step2_estimate": {"en": "2. Screening estimate", "pt": "2. Estimativa de triagem"},
    "nearest_line": {"en": "Nearest monitored site: **{code} — {name}** ({km} km away).",
                     "pt": "Local mais próximo: **{code} — {name}** ({km} km)."},
    "est_band": {"en": "Estimated risk band", "pt": "Faixa de risco estimada"},
    "est_explain": {"en": "Main factors:", "pt": "Principais fatores:"},
    "step3_action": {"en": "3. Suggested next actions", "pt": "3. Próximos passos"},
    "too_far": {"en": "No monitored site within 50 km — cannot estimate landscape risk reliably. "
                      "Your observation is still logged for researchers.",
                "pt": "Sem local monitorizado a 50 km — não é possível estimar de forma fiável."},
    "copilot_guardrail": {
        "en": "Guardrail: the estimate reuses the nearest monitored site's landscape features; "
              "the explanation is generated only from validated data and model coefficients.",
        "pt": "Proteção: a estimativa reutiliza o local mais próximo; explicação só de dados validados.",
    },
    "action_sample": {"en": "Sample again in 2 weeks to confirm.", "pt": "Amostrar de novo em 2 semanas."},
    "action_report": {"en": "Report the observation to your municipality.",
                      "pt": "Comunicar a observação ao município."},
    "action_avoid": {"en": "Avoid direct contact, especially after heavy rain.",
                     "pt": "Evitar contacto direto, sobretudo após chuva forte."},
    "action_notify": {"en": "Flag to the local water/health authority for inspection.",
                      "pt": "Sinalizar à autoridade de água/saúde para inspeção."},
    "quality_title": {"en": "Citizen data-quality triage", "pt": "Triagem de qualidade"},
    "quality_caption": {
        "en": "Every rule is deterministic and explainable, so an officer can trust the triage.",
        "pt": "Cada regra é determinística e explicável.",
    },
    "submissions": {"en": "Submissions", "pt": "Submissões"},
    "needs_review": {"en": "Need review", "pt": "A rever"},
    "show_flagged": {"en": "Show only flagged", "pt": "Mostrar só sinalizados"},
    "about_title": {"en": "About & interoperability", "pt": "Sobre e interoperabilidade"},
    "about_body": {
        "en": "AquaSentinel is a hackathon prototype for the OneAquaHealth IEEE Global Hackathon. "
              "Data via the public OneAquaHealth Resilience Map API. It exposes sites and "
              "observations through an OGC SensorThings-shaped JSON and GeoJSON API (see `api/`), "
              "with an optional FHIR Observation mapping to make the environment↔public-health "
              "link explicit.\n\n"
              "**Primary track:** Resilience Informatics. **Secondary:** Data-to-Insight, "
              "AI-Supported Assessment, Digital Health Standards.",
        "pt": "Protótipo para o OneAquaHealth IEEE Global Hackathon.",
    },
}


def t(key: str, lang: str = "en") -> str:
    entry = _STR.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key
