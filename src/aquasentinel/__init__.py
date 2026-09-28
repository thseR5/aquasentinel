"""AquaSentinel: One Health early-warning and insight platform for urban streams."""

__version__ = "0.1.0"

# Composite risk components (health_risks.csv). The composite healthRiskScore is
# the mean of these three; we always model the three components as the real targets.
RISK_COMPONENTS = ["scaledPathogenRisk", "scaledFecalRisk", "scaledArgRisk"]
COMPOSITE = "healthRiskScore"

# The five OneAquaHealth partner cities and the country each sits in. Used by the
# quality validator to flag citizen submissions that fall outside partner countries.
PARTNER_CITIES = {
    "CO": "Coimbra",
    "TO": "Toulouse",
    "GH": "Ghent",
    "BE": "Benevento",
    "OS": "Oslo",
}
